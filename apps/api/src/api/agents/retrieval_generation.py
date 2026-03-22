from google import genai
from groq import Groq
from qdrant_client import QdrantClient
from langsmith import traceable, get_current_run_tree
from pydantic import BaseModel, Field
import numpy as np
from qdrant_client.models import Filter, FieldCondition, MatchValue
from api.agents.utils.prompt_management import prompt_template_config
from api.core.config import config
import json


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

    for id, chunk, rating in zip(context["retrieved_context_ids"], context["retrieved_context"], context["retrieved_context_ratings"]):
        formatted_context += f"- ID: {id}, rating: {rating}, description: {chunk}\n"

    return formatted_context


@traceable(
    name="build_prompt",
    run_type="prompt"
)
def build_prompt(preprocessed_context, question):

    template = prompt_template_config("api/agents/prompts/retrieval_generation.yaml", "retrieval_generation")
    prompt = template.render(preprocessed_context=preprocessed_context, question=question)

    return prompt


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
    "answer": "your answer here",
    "references": [
        {"id": "product_id", "description": "short description"}
    ]
}
"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": system_prompt}],
        temperature=0,
    )

    raw_text = response.choices[0].message.content

    # Strip markdown code blocks if present
    raw_text = raw_text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
        return RAGGenerationResponse(
            answer=data.get("answer", ""),
            references=[RAGUsedContext(**ref) for ref in data.get("references", [])]
        )
    except (json.JSONDecodeError, Exception):
        return RAGGenerationResponse(
            answer=raw_text,
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

    for item in result.get("references", []):
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

            if points:
                payload = points[0].payload
                image_url = payload.get("image")
                price = payload.get("price")
                if image_url:
                    used_context.append({
                        "image_url": image_url,
                        "price": price,
                        "description": item.description
                    })
        except Exception:
            continue

    return {
        "answer": result["answer"],
        "used_context": used_context,
    }