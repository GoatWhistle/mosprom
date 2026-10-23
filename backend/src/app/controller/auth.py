from typing import Annotated

from fastapi import Depends, Header, Request

from app.controller.services import Services
from app.usecase.dto.instance import InstanceDTO


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


async def current_instance(
    services: Annotated[Services, Depends(get_services)],
    authorization: Annotated[str | None, Header()] = None,
) -> InstanceDTO:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    return await services.instances.authenticate(token)


ServicesDep = Annotated[Services, Depends(get_services)]
InstanceDep = Annotated[InstanceDTO, Depends(current_instance)]
