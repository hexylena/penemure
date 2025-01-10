from pydantic import BaseModel, Field
import os
from typing import Optional
import uuid


class UniformReference(BaseModel, frozen=True):
    app: str
    namespace: Optional[str] = None
    ident: str = Field(default_factory=lambda : str(uuid.uuid4()))

    def __repr__(self):
        return self.urn

    def _assemble(self) -> list[str]:
        parts = [self.app]
        if self.namespace:
            parts.append(self.namespace)
        parts.append(self.ident)
        return parts

    @property
    def url(self) -> str:
        return '/'.join(self._assemble())

    @property
    def urn(self) -> str:
        parts = ['urn', 'boshedron'] + self._assemble()
        return ':'.join(parts)

    @property
    def path(self) -> str:
        return os.path.join(*self._assemble())

    @classmethod
    def from_path(cls, end: str):
        app, rest = end.split('/', 1)
        if os.path.sep in rest:
            namespace, ident = rest.split('/', 1)
        else:
            namespace = None
            ident = rest
        return cls(app=app, namespace=namespace, ident=ident)

# TODO: probably should be more capable? URN style?
class Reference(BaseModel):
    id: UniformReference

class BlobReference(Reference):
    type: str

    @property
    def ext(self):
        if self.type == 'image/png':
            return '.png'
        return ".xyz"

class ExternalReference(BaseModel):
    url: str

class UnresolvedReference(BaseModel):
    path: str
    remote: bool = False

