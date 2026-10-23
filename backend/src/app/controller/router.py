from fastapi import APIRouter

from app.controller.conversations.router import router as conversations_router
from app.controller.health.router import router as health_router
from app.controller.instances.router import router as instances_router
from app.controller.plugin.router import router as plugin_router
from app.controller.runs.router import router as runs_router

api_router_v1 = APIRouter(prefix="/api/v1")
api_router_v1.include_router(health_router)
api_router_v1.include_router(instances_router)
api_router_v1.include_router(plugin_router)
api_router_v1.include_router(conversations_router)
api_router_v1.include_router(runs_router)
