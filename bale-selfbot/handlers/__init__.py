# handlers/__init__.py
from .start import router as start_router
from .panel import router as panel_router
from .messages import router as messages_router

__all__ = ["start_router", "panel_router", "messages_router"]