from google import genai
from groq import Groq
from qdrant_client import QdrantClient
from langsmith import traceable, get_current_run_tree
from pydantic import BaseModel, Field
import numpy as np
import logging
import json
import re
from qdrant_client.models import Filter, FieldCondition, MatchValue
from api.agents.utils.prompt_management import prompt_template_config
from api.core.config import config


logger = logging.getLogger(__name__)

# ── Clients ──
gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
groq_client = Groq(api_key=config.GROQ_API_KEY)


class RAGUsedContext(BaseModel):
    id: str = Field(description="The ID of the item used to answer the question")
    description: str = Field(description="Short description of the item used to answer the question")


class RAGGenerationResponse(BaseModel):
    answer: str = Field(description="The answer to the question")
    references: list[RAGUsedContext] = Field(description="List of items used to answer the question")


@traceable(
    name="embed_query",
    run_type="embedding",
    metadata={"ls_provider": "google", "ls_model_name": "gemini-embedding-001"}
)
def get_embedding(text, model="models/gemini-embedding-001"):
    response = gemini_client.models.embed_content(
        model=model,
        contents=text,
    )
    return response.embeddings[0].values


@traceable(
    name="retrieve_data",
    run_type="retriever"
)
def retrieve_data(query, qdrant_client, k=5):

    query_embedding = get_embedding(query)

    results = qdrant_client.query_points(
        collection_name="Amazon-items-collection-01",
        query=query_embedding,
        limit=k,
    )

    retrieved_context_ids = []
    retrieved_context = []
    similarity_scores = []
    retrieved_context_ratings = []

    for result in results.points:
        retrieved_context_ids.append(result.payload["parent_asin"])
        retrieved_context.append(result.payload["description"])
        retrieved_context_ratings.append(result.payload["average_rating"])
        similarity_scores.append(result.score)

    return {
        "retrieved_context_ids": retrieved_context_ids,
        "retrieved_context": retrieved_context,
        "retrieved_context_ratings": retrieved_context_ratings,
        "similarity_scores": similarity_scores,
    }


@traceable(
    name="format_retrieved_context",
    run_type="prompt"
)
def process_context(context):

    formatted_context = ""

    for id, chunk, rating in zip(
        context["retrieved_context_ids"],
        context["retrieved_context"],
        context["retrieved_context_ratings"]
    ):
        formatted_context += f"- ID: {id}, rating: {rating}, description: {chunk}\n"

    return formatted_context


@traceable(
    name="build_prompt",
    run_type="prompt"
)
def build_prompt(preprocessed_context, question):

    template = prompt_template_config(
        "api/agents/prompts/retrieval_generation.yaml",
        "retrieval_generation"
    )
    prompt = template.render(
        preprocessed_context=preprocessed_context,
        question=question
    )

    return prompt


def _clean_and_parse_json(raw_text: str) -> dict | None:
    """
    Robustly strip markdown fences and extract a JSON object from raw LLM output.
    Returns parsed dict or None if all attempts fail.

    Root cause handled: Groq returns the answer field with REAL newlines inside
    the JSON string value, which makes it invalid JSON. We fix this by collapsing
    actual newlines inside string values into the escaped \\n sequence.
    """
    text = raw_text.strip()

    # Step 1: Remove all markdown code fences
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Step 2: Attempt direct parse (works if JSON is valid)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 3: Fix unescaped newlines INSIDE string values.
    # Strategy: find the "answer" value between the first " after "answer":
    # and the last " before "references", and replace real newlines with \n
    def fix_multiline_strings(s: str) -> str:
        """Replace actual newlines inside JSON string values with escaped \\n"""
        result = []
        in_string = False
        i = 0
        while i < len(s):
            ch = s[i]
            if ch == '"' and (i == 0 or s[i-1] != '\\'):
                in_string = not in_string
                result.append(ch)
            elif ch == '\n' and in_string:
                # Replace real newline inside string with escaped \n
                result.append('\\n')
            elif ch == '\r' and in_string:
                # Skip carriage returns inside strings
                pass
            else:
                result.append(ch)
            i += 1
        return ''.join(result)

    fixed = fix_multiline_strings(text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Step 4: Last resort — find the outermost {} block and try fixing it too
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        candidate = fix_multiline_strings(json_match.group(0))
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


@traceable(
    name="generate_answer",
    run_type="llm",
    metadata={"ls_provider": "groq", "ls_model_name": "llama-3.3-70b-versatile"}
)
def generate_answer(prompt):

    system_prompt = prompt + """

You MUST respond with a valid JSON object only. No extra text, no markdown, no code blocks.
The JSON must have exactly this structure:
{
    "answer": "your answer here as plain text with bullet points using • character",
    "references": [
        {"id": "product_id", "description": "short description"}
    ]
}

IMPORTANT for the answer field:
- Start with one intro sentence
- Then list each product as: "1. Product Name (ID: xxx)"  
- Under each product, use • for each feature/spec
- Use • for bullet points (not * or -)
- Separate bullet points with \\n
- Do NOT use markdown formatting inside the answer string
- Keep it as plain readable text
"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": system_prompt}],
        temperature=0,
    )

    raw_text = response.choices[0].message.content
    logger.info(f"Raw LLM output (first 200 chars): {raw_text[:200]}")

    data = _clean_and_parse_json(raw_text)

    if data:
        answer_text = data.get("answer", "")
        refs = []
        for ref in data.get("references", []):
            try:
                refs.append(RAGUsedContext(**ref))
            except Exception as e:
                logger.warning(f"Skipping invalid reference {ref}: {e}")
                continue
        logger.info(f"Parsed answer (first 100 chars): {answer_text[:100]}")
        logger.info(f"Parsed {len(refs)} references: {[r.id for r in refs]}")
        return RAGGenerationResponse(answer=answer_text, references=refs)

    # Fallback: return raw text so at least something shows in the UI
    logger.warning("JSON parsing failed — returning raw text as answer")
    return RAGGenerationResponse(
        answer=raw_text.strip(),
        references=[]
    )


@traceable(
    name="rag_pipeline"
)
def rag_pipeline(question, qdrant_client, top_k=5):

    retrieved_context = retrieve_data(question, qdrant_client, top_k)
    preprocessed_context = process_context(retrieved_context)
    prompt = build_prompt(preprocessed_context, question)
    answer = generate_answer(prompt)

    final_result = {
        "answer": answer.answer,
        "references": answer.references,
        "question": question,
        "retrieved_context_ids": retrieved_context["retrieved_context_ids"],
        "retrieved_context": retrieved_context["retrieved_context"],
        "similarity_scores": retrieved_context["similarity_scores"]
    }

    return final_result


def rag_pipeline_wrapper(question, top_k=5):

    qdrant_client = QdrantClient(url=config.QDRANT_URL)

    result = rag_pipeline(question, qdrant_client, top_k)

    used_context = []
    dummy_vector = np.zeros(3072).tolist()

    references = result.get("references", [])
    logger.info(f"Total references to fetch images for: {len(references)}")

    for item in references:
        try:
            points = qdrant_client.query_points(
                collection_name="Amazon-items-collection-01",
                query=dummy_vector,
                limit=1,
                with_payload=True,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="parent_asin",
                            match=MatchValue(value=item.id)
                        )
                    ]
                )
            ).points

            if not points:
                logger.warning(f"Product {item.id} — NO POINTS FOUND in Qdrant")
                continue

            payload = points[0].payload
            image_url = payload.get("image")
            price = payload.get("price")

            logger.info(f"Product {item.id} — image_url: '{image_url}', price: {price}")

            if image_url:
                used_context.append({
                    "image_url": image_url,
                    "price": price,
                    "description": item.description
                })
            else:
                logger.warning(f"Product {item.id} — image_url is empty or None, skipping")

        except Exception as e:
            logger.error(f"Product {item.id} — EXCEPTION while fetching payload: {e}")
            continue

    logger.info(f"Final used_context count with images: {len(used_context)}")

    return {
        "answer": result["answer"],
        "used_context": used_context,
    }