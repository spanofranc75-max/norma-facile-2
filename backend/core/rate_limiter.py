"""
Centralized rate limiting for NormaFacile 2.0.

Protects AI-powered endpoints from:
- Accidental frontend loops
- Retry storms
- Excessive API costs (OpenAI)
- DoS on expensive operations

Usage in routes:
    from core.rate_limiter import limiter, ai_rate_limit, heavy_rate_limit

    @router.post("/ai-endpoint")
    @ai_rate_limit
    async def my_ai_endpoint(request: Request, ...):
        ...
"""
import logging
from functools import wraps
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

logger = logging.getLogger(__name__)


def _get_user_or_ip(request: Request) -> str:
    """Extract user_id from request state (set by auth middleware) or fall back to IP."""
    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        return user.get("user_id", get_remote_address(request))
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_or_ip)

# Rate limit strings (slowapi format)
AI_LIMIT = "10/minute"          # AI generation endpoints (OpenAI calls)
HEAVY_LIMIT = "20/minute"       # Heavy compute (PDF gen, batch ops)
STANDARD_LIMIT = "60/minute"    # Standard write endpoints


def ai_rate_limit(func):
    """Decorator for AI-powered endpoints. 10 req/min per user."""
    @limiter.limit(AI_LIMIT)
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


def heavy_rate_limit(func):
    """Decorator for heavy compute endpoints. 20 req/min per user."""
    @limiter.limit(HEAVY_LIMIT)
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper
