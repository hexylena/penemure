import json
import shutil
import hashlib
import os
from sqlglot.executor import execute
import glob
import uuid
from typing import Dict
from typing import Optional, Union
from .note import Note
from .refs import UniformReference
from .apps import ModelFromAttr, Account
from pydantic import BaseModel, Field, computed_field
from pydantic_core import to_json, from_json


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

    @classmethod
    def realise_from_path(cls, base, full_path):
        end = full_path.replace(base + os.path.sep, '')
        urn = UniformReference.from_path(end)

        return cls(
            urn=urn,
            created=os.path.getctime(full_path),
            updated=os.path.getmtime(full_path),
            size=os.path.getsize(full_path)
        )


class StoredThing(StoredBlob):
    data: Union[Note, Account]
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
        if self.data.suggested_ident:
            return UniformReference(app=self.urn.app, namespace=self.urn.namespace, ident=self.data.suggested_ident)
        return self.urn

    @classmethod
    def realise_from_path(cls, base, full_path):
        end = full_path.replace(base + os.path.sep, '')
        urn = UniformReference.from_path(end)
        print(end, repr(urn))

        with open(full_path, 'r') as f:
            # here we need to be smarter about which class we're using?
            data = from_json(f.read())
            res = ModelFromAttr(data).model_validate(data)

        if res.namespace != urn.namespace:
            print(f"Odd, {urn.namespace} != {res.namespace}")

        return cls(
            urn=urn,
            data=res,
            created=os.path.getctime(full_path),
            updated=os.path.getmtime(full_path),
            size=os.path.getsize(full_path)
        )


class FsBackend(BaseModel):
    name: str
    path: str
    data: Dict[UniformReference, Union[StoredThing, StoredBlob]] = Field(default=dict())

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
            if isinstance(v, StoredThing):
                self.save_item(v)

    def find(self, identifier: UniformReference) -> Union[StoredThing, StoredBlob]:
        return self.data[identifier]

    def get_path(self, identifier: UniformReference):
        st = self.find(identifier)
        return os.path.join(self.path, st.relative_path)

    def has(self, identifier: UniformReference):
        return identifier in self.data

    def resolve(self, ref: UniformReference) -> Union[StoredThing, StoredBlob]:
        return self.find(ref)

    def load(self):
        self.data = {}
        for path in glob.glob(self.path + '/**/*', recursive=True):
            if os.path.isdir(path):
                continue

            if 'file/blob/' in path:
                st = StoredBlob.realise_from_path(self.path, path)
            else:
                st = StoredThing.realise_from_path(self.path, path)

            self.data[st.identifier] = st


class OverlayEngine(BaseModel):
    backends: list[FsBackend]

    def load(self):
        for backend in self.backends:
            backend.load()

    def find(self, identifier: UniformReference):
        # Find the first version of this from all of our backends, to enable shadowing.
        for backend in self.backends:
            try:
                return backend.find(identifier)
            except KeyError:
                pass
        return None

    def get_path(self, st: Union[StoredThing, StoredBlob]):
        for backend in self.backends:
            try:
                return backend.get_path(st.identifier)
            except KeyError:
                pass

    def all(self):
        return [self.find(k) for k in self.keys()]

    def keys(self):
        all_keys = set()
        for backend in self.backends:
            all_keys.update(backend.data.keys())
        return all_keys

    def add(self, note: Note) -> StoredThing:
        st = StoredThing(data=note, urn=UniformReference(app=note.type, namespace=note.namespace))
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
