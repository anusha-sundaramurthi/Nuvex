
from google import genai
from groq import Groq
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Prefetch, FusionQuery, Document
from langsmith import traceable, get_current_run_tree
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from jinja2 import Template
from typing import Annotated, List, Any
from operator import add
import instructor
import numpy as np
import logging
import json
import re

from api.agents.utils.prompt_management import prompt_template_config
from api.core.config import config


logger = logging.getLogger(__name__)

# ── Clients ──
gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
groq_client = Groq(api_key=config.GROQ_API_KEY)
instructor_client = instructor.from_groq(groq_client)


# ── Pydantic Models ──

class RAGUsedContext(BaseModel):
    id: str = Field(description="The ID of the item used to answer the question")
    description: str = Field(description="Short description of the item used to answer the question")


class RAGGenerationResponse(BaseModel):
    answer: str = Field(description="The answer to the question")
    references: list[RAGUsedContext] = Field(description="List of items used to answer the question")


class IntentRouterResponse(BaseModel):
    question_relevant: bool
    answer: str


class QueryExpandResponse(BaseModel):
    expanded_query: List[str]


# ── LangGraph State ──

class RAGState(BaseModel):
    initial_query: str = ""
    question_relevant: bool = False
    intent_answer: str = ""
    expanded_query: List[str] = []
    retrieved_context: Annotated[List[str], add] = []
    retrieved_context_ids: Annotated[List[str], add] = []
    retrieved_context_ratings: Annotated[List[float], add] = []
    query: str = ""
    k: int = 5
    answer: str = ""
    references: List[Any] = []


# ── Embedding ──

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


# ── Intent Router Node ──

@traceable(
    name="intent_router_node",
    run_type="llm",
    metadata={"ls_provider": "groq", "ls_model_name": "llama-3.3-70b-versatile"}
)
def intent_router_node(state: RAGState) -> dict:

    template = prompt_template_config(
        "api/agents/prompts/intent_router_agent.yaml",
        "intent_router_agent"
    )
    prompt = template.render(question=state.initial_query)

    response = instructor_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_model=IntentRouterResponse,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return {
        "question_relevant": response.question_relevant,
        "intent_answer": response.answer,
    }


def intent_router_edge(state: RAGState) -> str:
    if state.question_relevant:
        return "query_expand_node"
    else:
        return "end"


# ── Query Expansion Node ──

@traceable(
    name="query_expand_node",
    run_type="llm",
    metadata={"ls_provider": "groq", "ls_model_name": "llama-3.3-70b-versatile"}
)
def query_expand_node(state: RAGState) -> dict:

    prompt_template = """You are part of a shopping assistant that can answer questions about products in stock.

<Example>
Question: Can I get earphones for me and a waterproof speaker.
Statements:
- Earphones.
- Waterproof speaker.
</Example>

Instructions:
- You will be given a question and you need to expand it into a list of statements for contextual search to retrieve relevant products.
- The statements should not overlap in context.
- Each statement should represent a single product intent.
- If the question is about a single product, return a list with a single statement.

<Question>
{{ query }}
</Question>
"""

    template = Template(prompt_template)
    prompt = template.render(query=state.initial_query)

    response = instructor_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_model=QueryExpandResponse,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return {"expanded_query": response.expanded_query}


def query_expand_edge(state: RAGState):
    """Fan out one retrieve_node per expanded query using Send()"""
    return [
        Send("retrieve_node", {"query": q, "k": state.k})
        for q in state.expanded_query
    ]


# ── Retriever Node ──

@traceable(
    name="retrieve_node",
    run_type="retriever"
)
def retrieve_node(state: dict) -> dict:

    query = state["query"] if isinstance(state, dict) else state.query
    k = state["k"] if isinstance(state, dict) else state.k

    qdrant_client = QdrantClient(url=config.QDRANT_URL)
    query_embedding = get_embedding(query)

    results = qdrant_client.query_points(
        collection_name="Amazon-items-collection-01",
        query=query_embedding,
        limit=k,
    )

    
    ids = []
    context = []
    ratings = []

    for result in results.points:
        ids.append(result.payload["parent_asin"])
        context.append(result.payload["description"])
        ratings.append(result.payload["average_rating"])

    return {
        "retrieved_context_ids": ids,
        "retrieved_context": context,
        "retrieved_context_ratings": ratings,
    }


# ── Aggregator Node ──

@traceable(
    name="format_retrieved_context",
    run_type="prompt"
)
def process_context(state: RAGState) -> str:
    formatted = ""
    for id_, chunk, rating in zip(
        state.retrieved_context_ids,
        state.retrieved_context,
        state.retrieved_context_ratings
    ):
        formatted += f"- ID: {id_}, rating: {rating}, description: {chunk}\n"
    return formatted


@traceable(
    name="aggregator_node",
    run_type="llm",
    metadata={"ls_provider": "groq", "ls_model_name": "llama-3.3-70b-versatile"}
)
def aggregator_node(state: RAGState) -> dict:

    preprocessed_context = process_context(state)

    template = prompt_template_config(
        "api/agents/prompts/retrieval_generation.yaml",
        "retrieval_generation"
    )
    prompt = template.render(
        preprocessed_context=preprocessed_context,
        question=state.initial_query
    )

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
        return {"answer": answer_text, "references": refs}

    logger.warning("JSON parsing failed — returning raw text as answer")
    return {"answer": raw_text.strip(), "references": []}


# ── LangGraph Pipeline ──

def build_rag_graph():

    workflow = StateGraph(RAGState)

    workflow.add_node("intent_router_node", intent_router_node)
    workflow.add_node("query_expand_node", query_expand_node)
    workflow.add_node("retrieve_node", retrieve_node)
    workflow.add_node("aggregator_node", aggregator_node)

    workflow.add_edge(START, "intent_router_node")

    workflow.add_conditional_edges(
        "intent_router_node",
        intent_router_edge,
        {
            "query_expand_node": "query_expand_node",
            "end": END
        }
    )

    workflow.add_conditional_edges("query_expand_node", query_expand_edge)

    workflow.add_edge("retrieve_node", "aggregator_node")
    workflow.add_edge("aggregator_node", END)

    return workflow.compile()


rag_graph = build_rag_graph()


# ── JSON Parsing Helper (unchanged from original) ──

def _clean_and_parse_json(raw_text: str) -> dict | None:
    text = raw_text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    def fix_multiline_strings(s: str) -> str:
        result = []
        in_string = False
        i = 0
        while i < len(s):
            ch = s[i]
            if ch == '"' and (i == 0 or s[i-1] != '\\'):
                in_string = not in_string
                result.append(ch)
            elif ch == '\n' and in_string:
                result.append('\\n')
            elif ch == '\r' and in_string:
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

    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        candidate = fix_multiline_strings(json_match.group(0))
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


# ── Public Wrapper (called by graph.py — same interface as before) ──

@traceable(name="rag_pipeline")
def rag_pipeline_wrapper(question: str, top_k: int = 5) -> dict:

    initial_state = {
        "initial_query": question,
        "k": top_k,
    }

    result = rag_graph.invoke(initial_state)

    # Off-topic question — intent router blocked it
    if not result.get("question_relevant", True) and not result.get("answer"):
        return {
            "answer": result.get("intent_answer", "I can only answer questions about products in stock."),
            "used_context": [],
        }

    # Off-topic with a message from intent router
    if not result.get("question_relevant", True):
        return {
            "answer": result.get("intent_answer", ""),
            "used_context": [],
        }

    # Fetch images for references
    qdrant_client = QdrantClient(url=config.QDRANT_URL)
    dummy_vector = np.zeros(3072).tolist()
    used_context = []

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

            if not points:
                logger.warning(f"Product {item.id} — NO POINTS FOUND in Qdrant")
                continue

            payload = points[0].payload
            image_url = payload.get("image")
            price = payload.get("price")

            if image_url:
                used_context.append({
                    "image_url": image_url,
                    "price": price,
                    "description": item.description
                })
            else:
                logger.warning(f"Product {item.id} — image_url is empty, skipping")

        except Exception as e:
            logger.error(f"Product {item.id} — EXCEPTION: {e}")
            continue

    logger.info(f"Final used_context count: {len(used_context)}")

    return {
        "answer": result.get("answer", ""),
        "used_context": used_context,
    }