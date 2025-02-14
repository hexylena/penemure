from fastapi.openapi.models import HTTPBase as HTTPBaseModel
import os
from pydantic import ConfigDict
import starlette.status as status
from fastapi import FastAPI, HTTPException, Form, Response, Request, UploadFile
from pydantic import BaseModel
from typing import Optional
from typing_extensions import Annotated, Doc
import socket


class PenemureAuth(HTTPBaseModel, frozen=True):
    scheme: str = 'basic'


class PenemureCredentials(BaseModel):
    name: str
    username: str
    namespace: str


class RemoteUserAuthentication(PenemureAuth):
    header: str = 'REMOTE_USER'

    async def __call__(  # type: ignore
        self, request: Request
    ) -> Optional[PenemureCredentials]:
        user = request.headers.get(self.header)

        if not user or user == "":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        return PenemureCredentials(username=user, name=user, namespace='remote')


class TailscaleHeaderAuthentication(PenemureAuth):
    scheme: str = 'basic'
    # model_config = ConfigDict(validate_assignment=False)

    async def __call__(  # type: ignore
        self, request: Request
    ) -> Optional[PenemureCredentials]:
        user = request.headers.get('Tailscale-User-Login') # hexylena@github
        name = request.headers.get('Tailscale-User-Name') # Helena
        if user is None or name is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        return PenemureCredentials(username=user, name=name, namespace='tailscale')


class LocalUserAuthentication(PenemureAuth):
    scheme: str = 'basic'

    async def __call__(  # type: ignore
        self, request: Request
    ) -> Optional[PenemureCredentials]:
        user = os.environ['USER']
        host = socket.gethostname()
        return PenemureCredentials(username=user, name=user, namespace=host)
