import itertools
import datetime
import json
import subprocess
import os
import glob

from .note import Note
from .refs import UniformReference
from .sqlish import GroupedResultSet, ResultSet, extract_groups
from .note import Note
from .refs import UniformReference
from .apps import ModelFromAttr, Account
from pydantic import BaseModel
from pydantic import BaseModel, Field, computed_field, PastDatetime
from pydantic_core import to_json, from_json
from sqlglot import parse_one, exp
from sqlglot.executor import execute
from typing import Dict
from typing import Optional, Union
from typing import Optional, Union


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
        end = full_path.replace(base, '').lstrip('/')
        urn = UniformReference.from_path(end)

        return cls(
            urn=urn,
            created=os.path.getctime(full_path),
            updated=os.path.getmtime(full_path),
            size=os.path.getsize(full_path)
        )

    def clean_dict(self):
        raise NotImplementedError()


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

    @computed_field
    @property
    def identifier(self) -> UniformReference:
        return self.urn

    @classmethod
    def realise_from_path(cls, base, full_path):
        end = full_path.replace(base, '').lstrip('/')
        urn = UniformReference.from_path(end)

        with open(full_path, 'r') as f:
            # here we need to be smarter about which class we're using?
            data = from_json(f.read())
            res = ModelFromAttr(data).model_validate(data)

        if res.namespace != urn.namespace:
            print(f"Odd, {urn.namespace} != {res.namespace} (end={end})")

        return cls(
            urn=urn,
            data=res,
            created=os.path.getctime(full_path),
            updated=os.path.getmtime(full_path),
            size=os.path.getsize(full_path)
        )


class BaseBackend(BaseModel):
    name: str
    description: str
    path: str

    @property
    def html_title(self):
        return f'{self.description} ({self.name})'

    @classmethod
    def discover_meta(cls, path):
        meta = os.path.join(path, 'meta.json')
        if os.path.exists(meta):
            with open(meta, 'r') as handle:
                data = json.load(handle)
        else:
            data = {'name': path, 'description': ''}
            with open(meta, 'w') as handle:
                json.dump(data, handle)
        data['path'] = path
        return data

    @classmethod
    def discover(cls, path):
        data = cls.discover_meta(path)
        return cls.model_validate(data)

    def __repr__(self):
        return f'GitJsonFilesBackend(name={self.name}, description={self.description}, path={self.path})'


class GitJsonFilesBackend(BaseBackend):
    data: Dict[UniformReference, Union[StoredThing, StoredBlob]] = Field(default=dict())
    last_update: PastDatetime = None
    latest_commit: str = None

    @classmethod
    def discover(cls, path):
        data = cls.discover_meta(path)
        commit, commitdate = subprocess.check_output([
            'git', 'log', '-n', '1', '--format=%H %at',
        ], cwd=path).decode('utf-8').strip().split(' ')
        data['latest_commit'] = commit
        data['last_update'] = datetime.datetime.fromtimestamp(int(commitdate))

        return cls.model_validate(data)

    def sync(self):
        if self.last_update is not None:
            pass # todo logic to not push/pull too frequently

        has_changes = subprocess.check_output(['git', 'diff-index', 'HEAD', '.'], cwd=self.path)
        new_files =  subprocess.check_output(['git', 'ls-files', '--other', '--directory', '--exclude-standard'], cwd=self.path)
        if len(has_changes) > 0 or len(new_files) > 0:
            print(f'{self.path} has changes, {len(has_changes)} || len({new_files})')
            subprocess.check_call(['git', 'add', '.'], cwd=self.path)
            subprocess.check_call(['git', 'commit', '-m', 'automatic'], cwd=self.path)

        subprocess.check_call(['git', 'pull', '--rebase', 'origin'], cwd=self.path)
        subprocess.check_call(['git', 'push', 'origin'], cwd=self.path)

    def save_item(self, stored_thing: StoredThing, fsync=True):
        """Save updates to an existing file."""
        self.data[stored_thing.identifier] = stored_thing

        full_path = os.path.join(self.path, stored_thing.relative_path)
        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        stored_thing.data.persist_attachments(os.path.join(self.path, 'file', 'blob'))

        with open(full_path, 'wb') as f:
            f.write(to_json(stored_thing.data))

        if fsync:
            self.sync()

    def remove_item(self, stored_thing: StoredThing, fsync=True):
        del self.data[stored_thing.identifier]
        full_path = os.path.join(self.path, stored_thing.relative_path)
        os.unlink(full_path)
        if fsync:
            self.sync()

    def save(self, fsync=True):
        for v in self.data.values():
            if isinstance(v, StoredThing):
                self.save_item(v, fsync=fsync)

    def find(self, identifier: UniformReference) -> Union[StoredThing, StoredBlob]:
        if identifier in self.data:
            return self.data[identifier]

        for ident, ref in self.data.items():
            if ident.ident == identifier.ident:
                return ref
        raise KeyError(f"Could not find {identifier.ident}")

    def find_s(self, identifier: str) -> StoredThing | StoredBlob:
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

            # Ignore backend meta
            if path.replace(self.path.rstrip('/') + '/', '') == 'meta.json':
                continue

            print('realising', self.path, path)

            if 'file/blob/' in path:
                st = StoredBlob.realise_from_path(self.path, path)
            else:
                st = StoredThing.realise_from_path(self.path, path)

            self.data[st.identifier] = st


class WrappedStored(BaseModel):
    thing: StoredThing | StoredBlob
    backend: Optional[GitJsonFilesBackend] = None

    def not_blob(self):
        return isinstance(self.thing, StoredThing)


class WrappedStoredThing(BaseModel):
    thing: StoredThing
    backend: GitJsonFilesBackend

    def not_blob(self):
        return True

    def clean_dict(self, oe=None):
        d = self.thing.data.model_dump()
        d['id'] = self.thing.urn.urn
        d['backend'] = self.backend.name

        for k in ('contents', 'attachments', 'tags'):
            if k in d:
                del d[k]

        # TODO: shadowing?
        for tag in self.thing.data.tags:
            d[tag.key] = tag.render()

        # TODO: web+boshedron: also works as a prefix instead of #url as a suffix.
        d['title'] = f'<a href="{self.thing.urn.urn}#url">{self.thing.html_title}</a>'
        d['title_plain'] = f'{self.thing.html_title}'
        #d['contributors'] = self.thing.data.get_contributors(oe)

        if d['parents'] is not None and len(d['parents']) > 0:
            d['parents'] = ' XX '.join([x.urn for x in self.thing.data.get_parents()])
        else:
            d['parents'] = None

        return d

def narrow_thing(s: WrappedStored) -> WrappedStoredThing:
    if isinstance(s.thing, StoredThing):
        return WrappedStoredThing(thing=s.thing, backend=s.backend)
    raise Exception()



class OverlayEngine(BaseModel):
    backends: list[GitJsonFilesBackend]

    def load(self):
        for backend in self.backends:
            backend.load()

    def find(self, identifier: (UniformReference | str)) -> WrappedStored:
        # Find the first version of this from all of our backends, to enable shadowing.
        for backend in self.backends:
            try:
                if isinstance(identifier, str):
                    return WrappedStored(thing=backend.find_s(identifier), backend=backend)
                return WrappedStored(thing=backend.find(identifier), backend=backend)
            except KeyError:
                pass
        raise KeyError(f"Cannot find {identifier}")

    def migrate_backend(self, identifier: (UniformReference | str), backend: GitJsonFilesBackend) -> None:
        ws = narrow_thing(self.find(identifier))
        return self.migrate_backend_thing(ws=ws, backend=backend)

    def migrate_backend_thing(self, ws: WrappedStoredThing, backend: GitJsonFilesBackend) -> None:
        if ws.backend == backend:
            # Already in the right place
            return

        # Save to new backend
        if not isinstance(ws.thing, StoredThing):
            raise NotImplementedError("Haven't handled stored blob migration")

        backend.save_item(ws.thing, fsync=False)

        # Remove from old backend
        ws.backend.remove_item(ws.thing, fsync=False)

    def find_thing(self, identifier: (UniformReference | str)) -> WrappedStoredThing:
        return narrow_thing(self.find(identifier=identifier))

    def get_path(self, st: Union[StoredThing, StoredBlob, WrappedStored, WrappedStoredThing]) -> str:
        if isinstance(st, WrappedStored) or isinstance(st, WrappedStoredThing):
            ident = st.thing.identifier
        else:
            ident = st.identifier

        for backend in self.backends:
            try:
                return backend.get_path(ident)
            except KeyError:
                pass
        raise KeyError(f"Cannot find {ident}")

    def all(self) -> list[WrappedStored]:
        t = [self.find(k) for k in self.keys()]
        return t

    def all_things(self) -> list[WrappedStoredThing]:
        return [narrow_thing(x) for x in self.all() if x.not_blob()]

    def keys(self) -> set[UniformReference]:
        all_keys = set()
        for backend in self.backends:
            all_keys.update(backend.data.keys())
        return all_keys

    def add(self, note: Note, backend: Optional[GitJsonFilesBackend]=None, fsync=False) -> WrappedStoredThing:
        st = StoredThing(data=note, urn=UniformReference(app=note.type, namespace=note.namespace))
        be = self.save_item(st, backend=backend, fsync=fsync)
        return WrappedStoredThing(thing=st, backend=be)

    def save_thing(self, ws: WrappedStoredThing, fsync=False) -> GitJsonFilesBackend:
        return self.save_item(stored_thing=ws.thing, backend=ws.backend, fsync=fsync)

    def save_item(self, stored_thing: StoredThing, backend: Optional[GitJsonFilesBackend]=None, fsync=False) -> GitJsonFilesBackend:
        b = None

        # TODO: Migrating?
        if backend is not None:
            for be in self.backends:
                if be.name == backend:
                    b = be
                    break

        for be in self.backends:
            if be.has(stored_thing.identifier):
                b = be
                break

        if b is None:
            b = self.backends[0]

        b.save_item(stored_thing, fsync=fsync)
        return b

    def save(self, fsync=True) -> None:
        for backend in self.backends:
            backend.save(fsync=fsync)

    def search(self, **kwargs) -> list[WrappedStoredThing]:
        results = []
        custom = None
        if 'custom' in kwargs:
            custom = kwargs['custom']
            del kwargs['custom']

        for st in self.all():
            if not isinstance(st.thing, StoredThing): continue

            add = True
            for k, v in kwargs.items():
                if not hasattr(st.thing.data, k):
                    add = False
                    continue

                if getattr(st.thing.data, k) != v:
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

    def make_a_db(self, ensure_present):
        notes = [x.clean_dict(self)
                 for x in self.all_things()]

        # We have an 'all' table if you just want to search all types.
        # or individual tables can be searched by type.
        tables = {'__all__': []}
        for note in notes:
            if note['type'] not in tables:
                tables[note['type']] = []
            tables[note['type']].append(note)
            tables['__all__'].append(note)

        known_apps = [p.model_fields['type'].default for p in Note.__subclasses__()] + [Note.model_fields['type'].default]
        for app in known_apps:
            if app not in tables:
                tables[app] = []

        tables['__backend__'] = [
            {
                'id': b.name,
                'name': b.name,
                'description': b.description,
                'path': b.path,
                'last_commit': b.latest_commit,
                'last_update': b.last_update,
            }
            for b in self.backends
        ]

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

        tables = {k: fix_tags(v, ensure=ensure_present)
                  for k, v in tables.items()}

        # import pprint
        # pprint.pprint(tables)
        return tables

    def query(self, query, via=None, sql=False) -> Optional[GroupedResultSet]:
        # Allow overriding with keywords
        if query.split(' ')[0] == 'GROUP':
            sql = False
            query = ' '.join(query.split(' ')[1:])
        elif query.split(' ')[0] == 'SQL':
            sql = True
            query = ' '.join(query.split(' ')[1:])

        if via is not None and 'SELF' in query:
            query = query.replace('SELF', via.urn)

        res = parse_one(query)

        # Not strictly correct, since e.g. where's might be included but. acceptable.
        selects = [x.this.this for x in list(res.find_all(exp.Column))]
        tables = self.make_a_db(selects)

        # TODO: add any group by clauses to the select, otherwise we won't get
        # that data back! they can then be hidden afterwards.
        # TODO: maybe also add 'id' to the selects automatically? Or, a 'link' field?
        def groupless_behaviour(node):
            if isinstance(node, exp.Group):
                return None
            return node


        # a version without any group by
        if sql:
            desired_groups = []
            groupless_query = res.sql()
        else:
            desired_groups = list(res.find_all(exp.Group))
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

    def get_id(self):
        return UniformReference(app='none').ident

    def get_backend(self, name: str) -> GitJsonFilesBackend:
        for b in self.backends:
            if b.name == name:
                return b
        raise KeyError(f"Could not find {name}")
