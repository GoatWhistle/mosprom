from fastapi import APIRouter
from pydantic import BaseModel

from app.controller.auth import InstanceDep, ServicesDep

router = APIRouter(prefix="/instances", tags=["instances"])


class RegisterRequest(BaseModel):
    instance_id: str


class RegisterResponse(BaseModel):
    instance_id: str
    token: str


class LlmSettingsRequest(BaseModel):
    base_url: str
    model: str
    api_key: str


class StatusResponse(BaseModel):
    status: str


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: RegisterRequest, services: ServicesDep) -> RegisterResponse:
    token = await services.instances.register(body.instance_id)
    return RegisterResponse(instance_id=body.instance_id, token=token)


@router.put("/llm", response_model=StatusResponse)
async def set_llm(
    body: LlmSettingsRequest, instance: InstanceDep, services: ServicesDep
) -> StatusResponse:
    services.instances.set_llm(instance.id, body.base_url, body.model, body.api_key)
    return StatusResponse(status="configured")
