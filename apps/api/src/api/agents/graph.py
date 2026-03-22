import json
import uuid
import asyncio
import logging
import traceback
from typing import AsyncGenerator

from api.agents.retrieval_generation import rag_pipeline_wrapper

logger = logging.getLogger(__name__)


async def rag_agent_stream_wrapper(query: str, thread_id: str) -> AsyncGenerator[str, None]:
    """
    Wraps rag_pipeline_wrapper and streams the result as SSE events.
    """

    yield "data: Searching for the best products...\n\n"

    try:
        logger.info(f"Starting RAG pipeline for query: {query}")

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            rag_pipeline_wrapper,
            query
        )

        logger.info(f"RAG pipeline completed. Answer: {result.get('answer', '')[:100]}")

        answer = result.get("answer", "I could not find an answer.")
        used_context = result.get("used_context", [])
        trace_id = str(uuid.uuid4())

        final_payload = {
            "type": "final_result",
            "data": {
                "answer": answer,
                "used_context": used_context,
                "trace_id": trace_id,
                "shopping_cart": []
            }
        }

        yield f"data: {json.dumps(final_payload)}\n\n"

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"RAG pipeline error: {str(e)}\n{error_details}")

        error_payload = {
            "type": "final_result",
            "data": {
                "answer": f"Sorry, something went wrong: {str(e)}",
                "used_context": [],
                "trace_id": str(uuid.uuid4()),
                "shopping_cart": []
            }
        }
        yield f"data: {json.dumps(error_payload)}\n\n"