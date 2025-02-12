from pydantic import BaseModel, Field
import re
import os
from typing import Optional
from pydantic import computed_field
import uuid
from .util import *


class UniformReference(BaseModel, frozen=True):
    app: str
    namespace: Optional[str] = None
    ident: str = Field(default_factory=lambda : str(uuid.uuid4()))

    def __repr__(self):
        return self.urn

    def _assemble(self) -> list[str]:
        parts = []
        if self.app == 'file' and self.namespace == 'blob':
            parts.append('file')
        if self.namespace:
            parts.append(self.namespace)
        parts.append(self.ident)
        return parts

    # @property
    # def url(self) -> str:
    #     return '/'.join(self._assemble())

    @property
    def urn(self) -> str:
        parts = ['urn', 'penemure'] + self._assemble()
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
        if urn[0:2] != ['urn', 'penemure']:
            raise Exception(f"Unknown URN prefix: {urn}")

        urn = urn[2:]
        # Not sure about this
        urn = [x for x in urn if x != '']
        if len(urn) == 0:
            raise Exception(f"Cannot parse empty URN")

        if len(urn) > 2 and urn[0] == 'file' and urn[1] == 'blob':
            return cls(app='file', namespace='blob', ident=urn[2])
        elif len(urn) == 2:
            return cls(app='x', namespace=urn[0], ident=urn[1])
        elif len(urn) == 1:
            return cls(app='x', namespace=None, ident=urn[0])
        else:
            raise Exception(f"Cannot parse URN: {raw_urn}")

    @classmethod
    def match_string(cls, a, b):
        urn_a = cls.from_string(a)
        urn_b = cls.from_string(b)
        return urn_a.ident == urn_b.ident

    @classmethod
    def rewrite_urns(cls, contents: str, prefix: str, oe) -> str:
        def urn_to_url(u: re.Match):
            urn_ref = cls.from_string(u.group(1))
            if urn_ref.urn != u.group(1):
                raise Exception(f"Maybe mis-parsed URN, {urn_ref.urn} != {u.group(1)}")

            if u.group(3) == "title":
                try:
                    ref = oe.find(urn_ref)
                    return ref.thing.html_title # should it be html by default?
                except KeyError:
                    return urn_ref.urn
            elif u.group(3) == "url":
                try:
                    ref = oe.find_thing_or_blob(urn_ref)
                    return os.path.join(prefix, ref.thing.url)
                except KeyError:
                    return urn_ref.urn
            elif u.group(3) == "link":
                try:
                    ref = oe.find(urn_ref)
                    url = os.path.join(prefix, ref.thing.url)
                    return f'<a href="{url}">{ref.thing.html_title}</a>' 
                except KeyError:
                    try:
                        ref = oe.find_blob(urn_ref)
                        url = os.path.join(prefix, ref.thing.url)
                        return f'<a href="{url}">{ref.thing.urn.urn}</a>' 

                    except KeyError:
                        return f'<a href="#">{urn_ref.urn}</a>' 
            elif u.group(3) == "embed":
                try:
                    ref = oe.find_blob(urn_ref)
                    url = os.path.join(prefix, ref.thing.url)
                    return f'<img src="{url}" />'
                except KeyError:
                    try:
                        ref = oe.find(urn_ref)
                        url = os.path.join(prefix, ref.thing.url)
                        return f'<a href="{url}">{ref.thing.html_title}</a>' 

                    except KeyError:
                        return f'<a href="#">Couldn\'t find {urn_ref.urn}</a>' 
            else:
                return urn_ref.urn

        contents = re.sub('(urn:penemure:[a-z0-9:./-]+)(#(title|url|link|embed))?', urn_to_url, contents)

        return contents

    @classmethod
    def new_file_urn(cls, ext=None):
        ident = str(uuid.uuid4())
        if ext:
            ident += '.' + ext
        return cls(app='file', namespace='blob', ident=ident)

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


class StoredBlob(BaseModel):
    urn: UniformReference
    created: Optional[float] = None
    updated: Optional[float] = None
    size: Optional[int] = None

    @computed_field
    @property
    def relative_path(self) -> str:
        return self.urn.path

    def ref(self) -> UniformReference:
        return self.urn

    def save(self, backend):
        backend.save(self)

    @computed_field
    @property
    def identifier(self) -> UniformReference:
        return self.urn

    def refresh_meta(self, full_path):
        self.created = os.path.getctime(full_path)
        self.updated = os.path.getmtime(full_path)
        self.size = os.path.getsize(full_path)

    @classmethod
    def realise_from_path(cls, base, full_path):
        end = rebase_path(full_path, base)
        urn = UniformReference.from_path(end)

        return cls(
            urn=urn,
            created=os.path.getctime(full_path),
            updated=os.path.getmtime(full_path),
            size=os.path.getsize(full_path)
        )

    def clean_dict(self):
        raise NotImplementedError()

    def human_size(self, suffix="B"):
        num = float(self.size or 0)
        for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
            if abs(num) < 1024.0:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.1f}Yi{suffix}"

    @property
    def url(self) -> str:
        return self.identifier.path
