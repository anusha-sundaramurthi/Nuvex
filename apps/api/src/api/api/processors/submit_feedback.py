import logging
from langsmith import Client

logger = logging.getLogger(__name__)


def submit_feedback(
    trace_id: str,
    feedback_score: int | None,
    feedback_text: str,
    feedback_source_type: str
):
    """Submit feedback to LangSmith."""
    try:
        client = Client()
        client.create_feedback(
            run_id=trace_id,
            key="user_feedback",
            score=feedback_score,
            comment=feedback_text,
            source_type=feedback_source_type,
        )
        logger.info(f"Feedback submitted for trace_id: {trace_id}")
    except Exception as e:
        logger.error(f"Failed to submit feedback: {str(e)}")