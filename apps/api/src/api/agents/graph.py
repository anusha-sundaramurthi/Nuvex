import json
import uuid
import asyncio
import logging
import traceback
import re
from typing import AsyncGenerator

from api.agents.retrieval_generation import rag_pipeline_wrapper

logger = logging.getLogger(__name__)


def format_answer_as_html(text: str) -> str:
    """
    Convert the plain-text answer into clean HTML:
    - Intro sentence as a paragraph
    - Numbered products as bold headers
    - Bullet features under each product as <ul><li>
    """
    if not text:
        return text

    # Safety: if raw JSON leaked through, extract answer field
    if text.strip().startswith("{"):
        try:
            fixed = text.replace('\r\n', '\n')
            data = json.loads(fixed)
            if isinstance(data, dict) and "answer" in data:
                text = data["answer"]
        except (json.JSONDecodeError, Exception):
            answer_match = re.search(r'"answer"\s*:\s*"(.*?)"(?=\s*,\s*"references")', text, re.DOTALL)
            if answer_match:
                text = answer_match.group(1).replace('\\n', '\n')

    text = text.replace('\\n', '\n')

    lines = text.split('\n')
    html_parts = []
    in_list = False
    product_counter = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            continue

        is_bullet = (
            stripped.startswith('• ') or
            stripped.startswith('* ') or
            stripped.startswith('- ')
        )

        numbered_match = re.match(r'^(\d+)[.)]\s+(.+)$', stripped)

        if numbered_match:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            product_counter += 1
            product_name = numbered_match.group(2)
            product_name = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', product_name)
            html_parts.append(
                f'<p style="margin:14px 0 4px 0; font-weight:700; font-size:1rem; color:#1a1a2e;">'
                f'{product_counter}. {product_name}</p>'
            )

        elif is_bullet:
            if not in_list:
                html_parts.append('<ul style="margin:4px 0 8px 20px; padding:0;">')
                in_list = True
            content = stripped[2:].strip()
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            html_parts.append(
                f'<li style="margin-bottom:4px; line-height:1.6; color:#333;">{content}</li>'
            )

        else:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            formatted = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', stripped)
            html_parts.append(
                f'<p style="margin:6px 0; line-height:1.7; color:#1a1a2e;">{formatted}</p>'
            )

    if in_list:
        html_parts.append('</ul>')

    return ''.join(html_parts)


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

        raw_answer = result.get("answer", "I could not find an answer.")
        logger.info(f"RAG pipeline completed. Answer preview: {raw_answer[:120]}")

        answer_html = format_answer_as_html(raw_answer)

        used_context = result.get("used_context", [])
        trace_id = str(uuid.uuid4())

        final_payload = {
            "type": "final_result",
            "data": {
                "answer": answer_html,
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