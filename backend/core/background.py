"""Safe background task helper — wraps asyncio.create_task with error logging."""
import asyncio
import logging

logger = logging.getLogger(__name__)


def safe_background_task(coro, task_name: str = "background"):
    """Fire-and-forget with error logging. Replaces bare asyncio.create_task()."""
    async def _wrapper():
        try:
            await coro
        except Exception as e:
            logger.error(f"[BACKGROUND] Task '{task_name}' failed: {type(e).__name__}: {e}", exc_info=True)

    return asyncio.create_task(_wrapper(), name=task_name)
