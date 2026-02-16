from .datasets import router as datasets_router
from .projects import router as projects_router
from .scripts import router as scripts_router
from .chat import router as chat_router
from .settings import router as settings_router

__all__ = [
    "datasets_router",
    "projects_router",
    "scripts_router",
    "chat_router",
    "settings_router",
]
