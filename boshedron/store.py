import json
import shutil
import hashlib
import os
import glob
import uuid
from typing import Dict
from typing import Optional, Union
from .note import Note, Reference
from .apps import ModelFromAttr, Account
from pydantic import BaseModel, Field, computed_field
from pydantic_core import to_json, from_json


class StoredThing(BaseModel):
    data: Union[Note, Account]
    ident: str = Field(default_factory=lambda : str(uuid.uuid4()))
    created: Optional[float] = None
    updated: Optional[float] = None
    size: Optional[int] = None

    @computed_field
    @property
    def relative_path(self) -> str:
        return os.path.join(self.data.type, self.identifier)

    def ref(self) -> Reference:
        return Reference(id=self.identifier)

    def save(self, backend):
        backend.save(self)

    @computed_field
    @property
    def identifier(self) -> str:
        if self.data.namespace:
            if self.data.suggested_ident:
                return os.path.join(self.data.namespace, self.data.suggested_ident)
            return os.path.join(self.data.namespace, self.ident)
        elif self.data.suggested_ident:
            return self.data.suggested_ident
        return self.ident

    @classmethod
    def realise_from_path(cls, base, full_path):
        with open(full_path, 'r') as f:
            # here we need to be smarter about which class we're using?
            data = from_json(f.read())
            res = ModelFromAttr(data).model_validate(data)

        end = full_path.replace(base + os.path.sep, '')
        _app, rest = end.split('/', 1)
        if os.path.sep in rest:
            namespace, ident = rest.split('/', 1)
        else:
            namespace = None
            ident = rest

        if res.namespace != namespace:
            print(f"Odd, {namespace} != {res.namespace}")

        return cls(
            data=res,
            ident=ident,
            created=os.path.getctime(full_path),
            updated=os.path.getmtime(full_path),
            size=os.path.getsize(full_path)
        )

    def export(self):
        return self.data.export()


class FsBackend(BaseModel):
    name: str
    path: str
    data: Dict[str, StoredThing] = Field(default=dict)

    def save_item(self, stored_thing: StoredThing):
        """Save updates to an existing file."""
        self.data[stored_thing.identifier] = stored_thing

        full_path = os.path.join(self.path, stored_thing.relative_path)
        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        stored_thing.data.persist_attachments(os.path.join(self.path, 'file', 'blob'))

        with open(full_path, 'wb') as f:
            f.write(to_json(stored_thing.data))

    def save(self):
        for v in self.data.values():
            self.save_item(v)

    def find(self, identifier: str):
        return self.data[identifier]

    def has(self, identifier: str):
        return identifier in self.data

    def resolve(self, ref: Reference) -> StoredThing:
        return self.find(ref.id)

    def load(self):
        self.data = {}
        for path in glob.glob(self.path + '/**/*', recursive=True):
            if os.path.isdir(path):
                continue

            if 'file/blob/' in path:
                continue

            st = StoredThing.realise_from_path(self.path, path)
            self.data[st.identifier] = st


class OverlayEngine(BaseModel):
    backends: list[FsBackend]

    def load(self):
        for backend in self.backends:
            backend.load()

    def find(self, identifier: str):
        # Find the first version of this from all of our backends, to enable shadowing.
        for backend in self.backends:
            try:
                return backend.find(identifier)
            except KeyError:
                pass
        return None

    def all(self):
        all_keys = set()
        for backend in self.backends:
            all_keys.update(backend.data.keys())

        return [self.find(k) for k in all_keys]

    def add(self, note: Note) -> StoredThing:
        st = StoredThing(data=note)
        self.save_item(st)
        return st

    def save_item(self, stored_thing: StoredThing):
        b = None
        for backend in self.backends:
            if backend.has(stored_thing.identifier):
                b = backend
                break
        else:
            b = self.backends[0]
        b.save_item(stored_thing)

    def save(self):
        for backend in self.backends:
            backend.save()
