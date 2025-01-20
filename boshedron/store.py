import json
import itertools
from sqlglot import parse_one, exp
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
from .sqlish import GroupedResultSet, ResultSet, extract_groups
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

    @property
    def html_title(self):
        return f'{self.data.icon} {self.data.title}'

    @computed_field
    @property
    def relative_path(self) -> str:
        return self.identifier.path

    def ref(self) -> UniformReference:
        return self.urn

    def save(self, backend):
        backend.save(self)

    def link(self) -> str:
        return os.path.join(self.relative_path + '.html')

    def clean_dict(self):
        d = self.data.model_dump()
        d['id'] = self.urn.urn

        for k in ('contents', 'attachments', 'tags'):
            if k in d:
                del d[k]

        # TODO: shadowing?
        for tag in self.data.tags:
            d[tag.key] = tag.render()

        # TODO: web+boshedron: also works as a prefix instead of #url as a suffix.
        d['title'] = f'<a href="{self.urn.urn}#url">{self.html_title}</a>'
        d['title_plain'] = f'{self.html_title}'

        if d['parents'] is not None and len(d['parents']) > 0:
            d['parents'] = ' XX '.join([x.urn for x in self.data.get_parents()])
        else:
            d['parents'] = None

        return d

    @computed_field
    @property
    def identifier(self) -> UniformReference:
        return self.urn

    @classmethod
    def realise_from_path(cls, base, full_path):
        end = full_path.replace(base + os.path.sep, '')
        urn = UniformReference.from_path(end)

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

    def find_s(self, identifier: str) -> Union[StoredThing, StoredBlob]:
        ufr = UniformReference.from_string(identifier)
        return self.find(ufr)

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

    def find(self, identifier: (UniformReference | str)):
        # Find the first version of this from all of our backends, to enable shadowing.
        for backend in self.backends:
            try:
                if isinstance(identifier, str):
                    return backend.find_s(identifier)
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

    def search(self, **kwargs):
        results = []
        custom = None
        if 'custom' in kwargs:
            custom = kwargs['custom']
            del kwargs['custom']

        for st in self.all():
            if not isinstance(st, StoredThing): continue

            add = True
            for k, v in kwargs.items():
                if not hasattr(st.data, k):
                    add = False
                    continue

                if getattr(st.data, k) != v:
                    add = False
            if add:
                results.append(st)

        if custom == 'open':
            results = [x for x in results if x.data.log_is_closed()]
        elif custom == 'not-open':
            results = [x for x in results if not x.data.log_is_closed()]

        return results

    @classmethod
    def group_by(cls, data: list[StoredThing], key):
        # not really a class method more of a utility? MOVE?

        def get_created_date(s: StoredThing) -> str:
            return str(s.data.created.date())

        groups = []
        data = sorted(data, key=get_created_date)[::-1]
        if key == 'day':
            groups = [(x, list(y)) for (x, y) in itertools.groupby(data, get_created_date)]
        else:
            raise Exception('unimplemented')

        return groups

    def query(self, query):
        notes = [x.clean_dict()
                 for x in self.all()
                 if isinstance(x, StoredThing)]

        # We have an 'all' table if you just want to search all types.
        # or individual tables can be searched by type.
        tables = {'__all__': []}
        for note in notes:
            if note['type'] not in tables:
                tables[note['type']] = []
            tables[note['type']].append(note)
            tables['__all__'].append(note)

        def fix_tags(items, ensure=[]):
            # ensure that every item has every key.
            keys = set()
            for i in items:
                keys |= set(i.keys())

            keys |= set(ensure)

            for i in items:
                for k in keys:
                    if k not in i:
                        i[k] = ""
            return items

        res = parse_one(query)

        # Not strictly correct, since e.g. where's might be included but. acceptable.
        selects = [x.this.this for x in list(res.find_all(exp.Column))]
        tables = {k: fix_tags(v, ensure=selects) for k, v in tables.items()}

        # TODO: add any group by clauses to the select, otherwise we won't get
        # that data back! they can then be hidden afterwards.
        # TODO: maybe also add 'id' to the selects automatically? Or, a 'link' field?
        def groupless_behaviour(node):
            if isinstance(node, exp.Group):
                return None
            return node

        desired_groups = list(res.find_all(exp.Group))

        # a version without any group by
        groupless_query = res.transform(groupless_behaviour).sql()
        print(res.sql())

        res = execute(groupless_query, tables=tables)
        r = ResultSet(title=None, header=list(res.columns), rows=list(res.rows))

        if len(r.rows) == 0:
            return None

        # if we don't want any groupings, just return as-is
        if len(desired_groups) == 0:
            return GroupedResultSet(groups=[r])

        # and pull out our desired groups
        desired_groups = desired_groups[0].sql().replace('GROUP BY ', '').split(',')
        return extract_groups(r, desired_groups)
