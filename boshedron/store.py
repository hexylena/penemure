import itertools
import time
import datetime
import json
import os
import glob
import sqlite3
from enum import Enum

from .note import Note
from .refs import UniformReference
from .sqlish import GroupedResultSet, ResultSet, extract_groups
from .note import Note
from .refs import UniformReference
from .apps import ModelFromAttr, Account
from .util import *
from .errr import *
from pydantic import BaseModel
from pydantic import BaseModel, Field, computed_field, PastDatetime
from pydantic_core import to_json, from_json
from sqlglot import parse_one, exp, transpile
from sqlglot.executor import execute
from typing import Dict, Generator
from typing import Optional, Union
from .refs import *


class MutatedEnum(Enum):
    untouched = 'Untouched'
    added = 'Added'
    modified = 'Modified'
    modified_unstaged = 'Unstaged Modification (Probably done externally)'
    deleted = 'Deleted'
    deleted_unstaged = 'Unstaged Deletion (Probably done externally)'

    @classmethod
    def parse(cls, s: str):
        if '->' in s:
            raise NotImplementedError("No support for renamed files yet")
        else:
            path = s[3:]

        print(f"s {s} -> path=|{path}|")

        if s[0] == 'M':
            return path, MutatedEnum.modified
        elif s[1] == 'M':
            # Modified but not staged
            return path, MutatedEnum.modified_unstaged
        elif s[0] == 'A':
            return path, MutatedEnum.added
        elif s[0] == 'D':
            return path, MutatedEnum.deleted
        elif s[1] == 'D':
            return path, MutatedEnum.deleted_unstaged
        else:
            raise NotImplementedError("Unsupported file state")

class StoredThing(StoredBlob):
    data: Union[Note, Account]
    created: Optional[float] = None
    updated: Optional[float] = None
    size: Optional[int] = None

    @property
    def html_title(self):
        return f'{self.data.icon} {self.data.title}'

    @property
    def txt_title(self):
        # TODO: rubbish way to strip html
        if self.data.icon and len(self.data.icon) < 4:
            return f'{self.data.icon} {self.data.title}'
        else:
            return self.data.title

    @computed_field
    @property
    def relative_path(self) -> str:
        return os.path.join(self.data.__class__.__name__.lower(),
                            self.identifier.path + '.json')

    def ref(self) -> UniformReference:
        return self.urn

    def save(self, backend):
        backend.save(self)

    @property
    def url(self) -> str:
        return os.path.join(self.data.__class__.__name__.lower(),
                            self.identifier.path + '.html')

    @computed_field
    @property
    def identifier(self) -> UniformReference:
        return self.urn

    @classmethod
    def realise_from_path(cls, base, full_path):
        end = full_path.replace(base, '').lstrip('/').rstrip('.json')
        urn = UniformReference.from_path(end)

        with open(full_path, 'r') as f:
            # here we need to be smarter about which class we're using?
            try:
                data = from_json(f.read())
                res = ModelFromAttr(data).model_validate(data)
            except ValueError as ve:
                raise ValueError(f"Error reading {full_path}: {ve}")

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
    icon: str = '💿'

    @property
    def html_title(self):
        return f'{self.icon} {self.name}: {self.description}'

    @classmethod
    def new_meta(cls, path, name, description='', icon='💿'):
        if not os.path.exists(path):
            os.makedirs(path)

        meta = os.path.join(path, 'meta.json')
        data = {'name': name, 'description': description, 'icon': icon}
        with open(meta, 'w') as handle:
            json.dump(data, handle, indent=2)

        return cls.discover_meta(path)

    @classmethod
    def discover_meta(cls, path):
        meta = os.path.join(path, 'meta.json')
        if os.path.exists(meta):
            with open(meta, 'r') as handle:
                data = json.load(handle)
        else:
            data = {'name': path, 'description': '', 'icon': ''}
            with open(meta, 'w') as handle:
                json.dump(data, handle, indent=2)
        data['path'] = path
        return data

    @classmethod
    def discover(cls, path):
        data = cls.discover_meta(path)
        return cls.model_validate(data)

    def save_blob(self, stored_blob: StoredBlob, fsync=True, data: Optional[bytes]=None):
        raise NotImplementedError(f"save_blob {stored_blob} {fsync} {data}")


    def save_item(self, stored_thing: StoredThing, fsync=True):
        raise NotImplementedError(f"save_blob {stored_thing} {fsync}")

    def remove_item(self, stored_thing: StoredThing, fsync=False):
        raise NotImplementedError(f"remote_item {stored_thing} {fsync}")

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'Backend(name={self.name}, description={self.description}, path={self.path})'


class WrappedStoredBlob(BaseModel):
    thing: StoredBlob
    backend: BaseBackend
    state: MutatedEnum = MutatedEnum.untouched

    def save(self, fsync=False):
        self.backend.save_blob(self.thing, fsync=fsync)

    def not_blob(self):
        return False

    @computed_field
    @property
    def relative_path(self) -> str:
        return self.thing.urn.path

    @computed_field
    @property
    def full_path(self) -> str:
        return os.path.join(self.backend.path, self.thing.urn.path)

    def clean_dict(self, oe=None, template=None):
        d = {}
        d['id'] = self.thing.urn.ident
        d['urn'] = self.thing.urn.urn
        return d


class WrappedStoredThing(BaseModel):
    thing: StoredThing
    backend: BaseBackend
    state: MutatedEnum = MutatedEnum.untouched

    def not_blob(self):
        return True

    def save(self, fsync=False):
        self.backend.save_item(self.thing, fsync=fsync)

    def get_template(self, oe):
        res = oe.search(type='template', title=self.thing.data.type)
        if len(res) > 0:
            return res[0]
        return None

    @property
    def relative_path(self) -> str:
        return self.thing.relative_path

    @property
    def full_path(self) -> str:
        return os.path.join(self.backend.path, self.thing.relative_path)

    def clean_dict(self, oe, template=None):
        d = self.thing.data.model_dump()
        d['id'] = self.thing.urn.ident
        d['urn'] = self.thing.urn.urn
        d['url'] = f"/redir/{self.thing.urn.urn}"
        d['backend'] = self.backend.name
        d['created'] = self.thing.data.created
        d['updated'] = self.thing.data.updated
        d['system'] = self.thing.data.type in ('template', )
        d['blurb'] = self.thing.data.blurb

        for k in ('contents', 'attachments', 'tags'):
            if k in d:
                del d[k]

        # TODO: shadowing?
        for tag in self.thing.data.tags:
            vv = tag.value(template)
            if isinstance(vv, datetime.datetime):
                d[tag.key] = vv.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                d[tag.key] = vv

        # TODO: web+boshedron: also works as a prefix instead of #url as a suffix.
        d['title'] = f'<a href="{self.thing.urn.urn}#url">{self.thing.html_title}</a>'
        d['title_plain'] = f'{self.thing.txt_title}'
        d['title_txt'] = f'{self.thing.data.title}'
        #d['contributors'] = self.thing.data.get_contributors(oe)

        if d['parents'] is not None and len(d['parents']) > 0:
            d['parents'] = ' '.join([x.urn for x in self.thing.data.get_parents()])
            try:
                d['parent_first_title'] = oe.find_thing(self.thing.data.parents[0].urn).thing.data.title
            except (KeyError, TypeError):
                d['parent_first_title'] = None

        else:
            d['parents'] = None
            d['parent_first_title'] = None
            # d['final_ancestor_first_title'] = None
            # if 'final_ancestor_first_title' not in d:
            #     d['final_ancestor_first_title'] = oe.find_thing(ancestor_chain[-1]).thing.data.title

        ancestors = []
        for ancestor_chain in oe.get_lineage(self):
            for thing in ancestor_chain:
                ancestors.append(thing.urn)
        d['ancestors'] = ' '.join(set(ancestors))
        return d



class GitJsonFilesBackend(BaseBackend):
    data: Dict[UniformReference, WrappedStoredThing] = Field(default=dict())
    blob: Dict[UniformReference, WrappedStoredBlob] = Field(default=dict())
    last_update: Optional[PastDatetime] = None
    latest_commit: Optional[str] = None

    @classmethod
    def discover(cls, path):
        data = cls.discover_meta(path)
        commit, commitdate = subprocess_check_output([
            'git', 'log', '-n', '1', '--format=%H %at',
        ], cwd=path).decode('utf-8').strip().split(' ')
        data['latest_commit'] = commit
        data['last_update'] = datetime.datetime.fromtimestamp(int(commitdate))

        return cls.model_validate(data)

    def sync(self):
        if self.last_update is not None:
            pass # todo logic to not push/pull too frequently

        has_changes = subprocess_check_output(['git', 'diff-index', 'HEAD', '.'], cwd=self.path)
        new_files =  subprocess_check_output(['git', 'ls-files', '--other', '--directory', '--exclude-standard'], cwd=self.path)
        if len(has_changes) > 0 or len(new_files) > 0:
            print(f'{self.path} has changes, {len(has_changes)} || len({new_files})')
            subprocess_check_call(['git', 'commit', '-m', f'automatic {self.name}'], cwd=self.path)

        subprocess_check_call(['git', 'pull', '--rebase'], cwd=self.path)
        subprocess_check_call(['git', 'push'], cwd=self.path)

    def save_item(self, stored_thing: StoredThing, fsync=True):
        """Save updates to an existing file."""
        if stored_thing.identifier not in self.data:
            state = MutatedEnum.added
        else:
            state = MutatedEnum.modified
        self.data[stored_thing.identifier] = WrappedStoredThing(thing=stored_thing, backend=self, state=state)


        full_path = os.path.join(self.path, stored_thing.relative_path)
        print(f'Saving to {full_path}')
        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        stored_thing.data.persist_attachments(os.path.join(self.path, 'file', 'blob'))

        with open(full_path, 'wb') as f:
            if not stored_thing.data.model_has_changed:
                print("Writing this despite no changes")
            f.write(to_json(stored_thing.data, indent=2))

        stored_thing.data.model_reset_changed()

        subprocess_check_call(['git', 'add', rebase_path(full_path, self.path)], cwd=self.path)

        if fsync:
            self.sync()

    def save_blob(self, stored_blob: StoredBlob, fsync=True, data: Optional[bytes]=None):
        """Save updates to an existing file."""
        if stored_blob.identifier not in self.data:
            state = MutatedEnum.added
        else:
            state = MutatedEnum.modified
        self.blob[stored_blob.identifier] = WrappedStoredBlob(thing=stored_blob, backend=self, state=state)

        full_path = os.path.join(self.path, stored_blob.relative_path)
        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        # stored_blob.data.persist_attachments(os.path.join(self.path, 'file',
        # 'blob'))
        # TODO: do we need to write to the blob at all??
        if data:
            with open(full_path, 'wb') as f:
                f.write(data)

        stored_blob.refresh_meta(full_path)
        subprocess_check_call(['git', 'add', rebase_path(full_path, self.path)], cwd=self.path)

        if fsync:
            self.sync()

    def remove_item(self, stored_thing: StoredThing, fsync=False):
        del self.data[stored_thing.identifier]
        full_path = os.path.join(self.path, stored_thing.relative_path)
        os.unlink(full_path)
        subprocess_check_call(['git', 'rm', rebase_path(full_path, self.path)], cwd=self.path)
        if fsync:
            self.sync()

    def save(self, fsync=True):
        for v in self.data.values():
            if isinstance(v, StoredThing):
                self.save_item(v, fsync=fsync)
            elif isinstance(v, StoredBlob):
                self.save_blob(v, fsync=fsync)

    def find(self, identifier: UniformReference) -> WrappedStoredThing:
        if identifier in self.data:
            return self.data[identifier]

        for ident, ref in self.data.items():
            if ident.ident == identifier.ident:
                return ref
        raise KeyError(f"Could not find {identifier.ident}")

    def find_s(self, identifier: str) -> WrappedStoredThing:
        ufr = UniformReference.from_string(identifier)
        return self.find(ufr)

    def find_blob(self, identifier: UniformReference) -> WrappedStoredBlob:
        if identifier in self.blob:
            return self.blob[identifier]

        for ident, ref in self.blob.items():
            if ident.ident == identifier.ident:
                return ref
        raise KeyError(f"Could not find {identifier.ident}")

    def find_blob_s(self, identifier: str) -> WrappedStoredBlob:
        ufr = UniformReference.from_string(identifier)
        return self.find_blob(ufr)

    def get_path(self, identifier: UniformReference):
        st = self.find(identifier)
        return os.path.join(self.path, st.relative_path)

    def has(self, identifier: UniformReference):
        return identifier in self.data

    def resolve(self, ref: UniformReference) -> WrappedStoredThing:
        return self.find(ref)

    def all_modified(self): # -> list[WrappedStoredThing]:
        res = []
        for item in self.data.values():
            if item.state != MutatedEnum.untouched:
                res.append(item)
        for item in self.blob.values():
            if item.state != MutatedEnum.untouched:
                res.append(item)
        return res

    def get_backend_modifications(self):
        # Get statuses for existing files
        statuses = subprocess_check_output(['git', 'status', '-s', '.'], cwd=self.path).decode('utf-8')
        statuses = [x for x in statuses.split('\n') if len(x) > 0]
        # Remove invalid empty line statuses
        if len(statuses) == 1 and len(statuses[0]) == 0:
            statuses = []
        return {
            path: status
            for path, status
            in map(MutatedEnum.parse, statuses)
        }

    def load(self):
        self.data = {}
        statuses = self.get_backend_modifications()

        for path in glob.glob(self.path + '/**/*', recursive=True):
            if os.path.isdir(path):
                continue

            # Ignore backend meta
            short_path = rebase_path(path, self.path)
            if short_path == 'meta.json':
                continue

            status = statuses.get(short_path, MutatedEnum.untouched)
            if '.' not in short_path:
                print("ERROR: missing file extension", short_path)

            if 'file/blob/' in path:
                st = StoredBlob.realise_from_path(self.path, path)
                self.blob[st.identifier] = WrappedStoredBlob(thing=st, backend=self, state=status)
            else:
                st = StoredThing.realise_from_path(self.path, path)
                self.data[st.identifier] = WrappedStoredThing(thing=st, backend=self, state=status)


class OverlayEngine(BaseModel):
    backends: list[GitJsonFilesBackend]

    def load(self):
        for backend in self.backends:
            backend.load()

    def find(self, identifier: (UniformReference | str)) -> WrappedStoredThing:
        # Find the first version of this from all of our backends, to enable shadowing.
        for backend in self.backends:
            try:
                if isinstance(identifier, str):
                    return backend.find_s(identifier)
                return backend.find(identifier)
            except KeyError:
                pass
        raise KeyError(f"Cannot find {identifier}")

    def migrate_backend(self, identifier: (UniformReference | str), backend: GitJsonFilesBackend) -> None:
        ws = self.find(identifier)
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

    def find_blob(self, identifier: (UniformReference | str)) -> WrappedStoredBlob:
        for backend in self.backends:
            try:
                if isinstance(identifier, str):
                    return backend.find_blob_s(identifier)
                return backend.find_blob(identifier)
            except KeyError:
                pass
        raise KeyError(f"Cannot find {identifier}")

    def find_thing(self, identifier: (UniformReference | str)) -> WrappedStoredThing:
        return self.find(identifier=identifier)

    def find_thing_or_blob(self, identifier: (UniformReference | str)) -> WrappedStoredThing | WrappedStoredBlob:
        try:
            return self.find(identifier=identifier)
        except KeyError:
            return self.find_blob(identifier=identifier)

    def find_thing_from_backend(self, identifier: UniformReference, backend: GitJsonFilesBackend) -> WrappedStoredThing:
        return backend.find(identifier)

    def get_path(self, st: Union[StoredThing, WrappedStoredThing]) -> str:
        if isinstance(st, WrappedStoredThing):
            ident = st.thing.identifier
        else:
            ident = st.identifier

        for backend in self.backends:
            try:
                return backend.get_path(ident)
            except KeyError:
                pass
        raise KeyError(f"Cannot find {ident}")

    def all(self) -> list[WrappedStoredThing]:
        t = [self.find(k) for k in self.keys()]
        return t

    def all_things(self) -> list[WrappedStoredThing]:
        return [x for x in self.all()]

    def all_modified(self) -> list[WrappedStoredThing]:
        return [x for x in self.all() if x.state != MutatedEnum.untouched]

    def all_blobs(self):
        for backend in self.backends:
            for blob in backend.blob.values():
                yield blob

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
        ws.backend.save_item(ws.thing, fsync=fsync)
        return ws.backend

    def save_item(self, stored_thing: StoredThing, backend: Optional[GitJsonFilesBackend]=None, fsync=False) -> GitJsonFilesBackend:
        if isinstance(backend, str):
            raise Exception("Backend was declared as a backend, not a string")
        b = None

        # If the backend is supplied directly
        if backend is not None:
            b = backend
            # for be in self.backends:
            #     if be.name == backend:
            #         b = be
            #         break

        # Try looking for existing BEs with this specific identifier
        if b is None:
            for be in self.backends:
                if be.has(stored_thing.identifier):
                    b = be
                    break

        # Otherwise we take the first available one.
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
            results = [x for x in results if x.thing.data.log_is_closed()]
        elif custom == 'not-open':
            results = [x for x in results if not x.thing.data.log_is_closed()]

        return results

    def templates(self):
        """List registered 'templates'"""
        tpls = [x.thing.data.title for x in self.all_things() if x.thing.data.type == 'template']
        # TODO: add templates to mix.
        res = list(set(tpls + [Note.model_fields['type'].default]))
        return sorted(res)

    def apps(self):
        """List registered 'apps'"""
        builtins = [p.model_fields['type'].default for p in Note.__subclasses__()]
        seen = [x.thing.data.type for x in self.all_things()]
        tpls = [x.thing.data.title for x in self.all_things() if x.thing.data.type == 'template']
        # TODO: add templates to mix.
        res = list(set(builtins + seen + tpls + [Note.model_fields['type'].default]))
        return sorted(res)

    @classmethod
    def group_by(cls, data: list[WrappedStoredThing], key):
        # not really a class method more of a utility? MOVE?

        def get_created_date(s: WrappedStoredThing) -> str:
            return str(s.thing.data.created.date())

        groups = []
        data = sorted(data, key=lambda x: x.thing.data.created)[::-1]
        if key == 'day':
            groups = [(x, list(y)) for (x, y) in itertools.groupby(data, get_created_date)]
        else:
            raise Exception('unimplemented')

        return groups

    _cache = None
    _cache_sqlite = None
    _enable_sqlite = True # os.environ.get('SQLITE', 'false') != 'false'
    def make_a_db(self, ensure_present):
        if self._cache_sqlite is None:
            self._cache_sqlite = sqlite3.connect(":memory:", check_same_thread=False)
            # self._cache_sqlite = sqlite3.connect(".cache")

        # Saves less time than I thought. hmm.
        # return self._make_a_db(ensure_present)
        if self._cache is None or any([x.thing.data.model_has_changed for x in self.all_things()]):
            # print("Loading SQL DB")
            res = self._make_a_db(ensure_present)
            # a = time.time()
            self._cache = res
            # print(f"Created HASH in {time.time() - a}")
            if self._enable_sqlite:
                # a = time.time()
                for table, rows in res.items():
                    if len(rows) == 0:
                        continue
                    okeys = sorted(rows[0].keys())
                    qokeys = [f"'{x}'" for x in okeys]
                    qqkeys = ['?'] * len(okeys)

                    stmt = f"DROP TABLE IF EXISTS {table}"
                    self._cache_sqlite.execute(stmt)

                    stmt = f"CREATE TABLE {table}({', '.join(qokeys)})"
                    self._cache_sqlite.execute(stmt)

                    data = [
                        [sqlite3_type(row[ok]) for ok in okeys]
                        for row in rows
                    ]
                    stmt = f"INSERT INTO {table} VALUES({', '.join(qqkeys)})"
                    self._cache_sqlite.executemany(stmt, data)
                self._cache_sqlite.commit()
                # print(f"Created SQLITE3 DB in {time.time() - a}")

            return res
        else:
            # print("Using cached SQL DB")
            return self._cache

    def _make_a_db(self, ensure_present):
        templates = {
            x.thing.data.title: x.thing.data
            for x in self.all_things()
            if x.thing.data.type == 'template'}


        notes = [x.clean_dict(self, template=templates.get(x.thing.data.type, None))
                 for x in self.all_things()]


        # We have an 'all' table if you just want to search all types.
        # or individual tables can be searched by type.

        tables = {'__all__': [], '__block__': []}
        for note in notes:
            if note['type'] not in tables:
                tables[note['type']] = []
            tables[note['type']].append(note)
            tables['__all__'].append(note)

        tables['__blobs__'] = []
        for blob in self.all_blobs():
            tables['__blobs__'].append({
                'id': blob.thing.urn.ident,
                'urn': blob.thing.urn.urn,
                'size': blob.thing.size,
                'backend': blob.backend.name,
                # mime?
            })


        tables['__attachments__'] = []
        for note in self.all_things():
            n = note.thing
            for block in n.data.get_contents():
                tables['__block__'].append(block.clean_dict(n.urn.urn))

            for (id, urn) in n.data.attachments:
                blob = self.find_blob(urn)
                tables['__attachments__'].append({
                    'id': id,
                    'urn': urn.urn,
                    'parent': note.thing.urn.urn,
                    'parent_title': note.thing.data.title,
                    'size': blob.thing.size,
                    'backend': blob.backend.name,
                })

        for app in self.apps():
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

        # Shitty meta description
        tables['__table__'] = []
        for table_name, rows in tables.items():
            if len(rows) == 0:
                continue
            for col, val in rows[0].items():
                tables['__table__'].append({
                    'table': table_name,
                    'column': col,
                    'type': str(type(val)).replace('<', '&lt;').replace('>', '&gt;')
                })

        return tables

    def query_type(self, query):
        if query[0:5].upper() == 'GROUP':
            return 'GROUP', query[5:].strip()
        elif query[0:3].upper() == 'SQL':
            return 'SQL', query[3:].strip()
        else:
            return 'SQL', query

    def fmt_query(self, query):
        qtype, qselect = self.query_type(query)
        # print('fmt query', qtype, qselect)
        return qtype + ' ' +transpile(qselect, pretty=True)[0]

    def query(self, query, via=None, sql=False) -> Optional[GroupedResultSet]:
        # Allow overriding with keywords
        qtype, qselect = self.query_type(query)
        if qtype == 'GROUP':
            sql = False
        elif qtype == 'SQL':
            sql = True
        else:
            sql = sql

        query = qselect

        if via is not None and 'SELF' in query:
            query = query.replace('SELF', via.ident)

        res = parse_one(query)
        # print(res.sql())

        # Not strictly correct, since e.g. where's might be included but. acceptable.
        selects = [x.this.this for x in list(res.find_all(exp.Column))]
        # print('before', selects)
        if len(selects) > 0:
            selects = [x.sql() for x in res]
        # print('after', selects)
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
            groupless_query = res.transform(groupless_behaviour)
            # We want to be sure that EVERY query also checks for the ID.
            # >>> res = parse_one('SELECT title_plain, created, updated, type, id, url FROM __all__ GROUP BY title_plain ORDER BY type, created ASC, updated DESC')
            # >>> res.args['expressions'].append(parse_one('id AS __internal__'))
            # I don't think this will handle CTEs well, so let's restrict it to GROUP sqlss
            groupless_query.args['expressions'].append(parse_one('id AS _internal_id_'))

            # TODO: Let's also be sure that the grouping expression is included, in case the user does a 
            # 'select title from __all__ group by type'
            # where we do fake sql and thus the grouping fails.

            # print(desired_groups, selects)

            # groupless_query.args['expressions'].append(parse_one('id AS _internal_id_'))

            # And turn it into sql properly
            groupless_query = groupless_query.sql()

        # print(f'=> {groupless_query}')

        # a = time.time()
        if self._cache_sqlite is None:
            raise Exception("DB was not built")

        results = self._cache_sqlite.execute(groupless_query)
        # print(f'Executed query in {time.time() - a}')
        header = [x.split(' AS ')[1] if ' AS ' in x else x for x in selects]
        r = ResultSet.build(header, list(results), has_id=not(sql))
        # r = ResultSet(title=None, header=header, rows=list(results))

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

    def get_lineage(self, note: WrappedStoredThing, lineage=None): # -> Generator[list[WrappedStoredThing]]:
        res = list(self._get_lineage(note, lineage=lineage))
        if res == [[]]:
            return []
        return res

    def _get_lineage(self, note: WrappedStoredThing, lineage=None): # -> Generator[list[WrappedStoredThing]]:
        parents = note.thing.data.get_parents()
        if len(parents) == 0:
            if lineage is not None:
                yield lineage
            else:
                yield []
        else:
            for p_urn in parents:
                try:
                    p = self.find(p_urn)
                    if lineage is not None:
                        yield from self.get_lineage(p, lineage=lineage + [p.thing.urn])
                    else:
                        yield from self.get_lineage(p, lineage=[p.thing.urn])
                except KeyError:
                    yield [p_urn]
