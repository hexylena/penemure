from pydantic import BaseModel, Field
import re
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

    @classmethod
    def from_string(cls, raw_urn: str):
        urn = raw_urn.split(':')
        if urn[0:2] != ['urn', 'boshedron']:
            raise Exception("Unknown URN prefix")

        urn = urn[2:]
        # Not sure about this
        urn = [x for x in urn if x != '']

        if len(urn) == 3:
            return cls(app=urn[0], namespace=urn[1], ident=urn[2])
        elif len(urn) == 2:
            return cls(app=urn[0], namespace=None, ident=urn[1])
        else:
            raise Exception("Cannot parse URN")

    @classmethod
    def rewrite_urns(cls, contents: str, prefix: str, oe) -> str:
        def urn_to_url(u: re.Match):
            urn_ref = cls.from_string(u.group(1))
            if urn_ref.urn != u.group(1):
                raise Exception(f"Maybe mis-parsed URN, {urn_ref.urn} != {u.group(1)}")

            if u.group(3) == "title":
                ref = oe.find(urn_ref)
                # print(ref, urn_ref.urn)
                return ref.thing.html_title # should it be html by default?
            elif u.group(3) == "url":
                return prefix + '/' + urn_ref.url + '.html'
            else:
                return urn_ref.urn
            # print(u, u.group(3), ref)
            # return prefix + '/' + '/'.join(u.group(0).split(':')[2:]) + '.html'

        contents = re.sub('(urn:boshedron:[a-z0-9:./-]+)(#(title|url))?', urn_to_url, contents)

        return contents

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

