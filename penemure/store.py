import itertools
import tempfile
import random
import string
import csv
import datetime
import json
import os
import glob
import hashlib
import sqlite3
from enum import Enum

from .note import Note
from .refs import UniformReference
from .sqlish import GroupedResultSet, ResultSet, extract_groups
from .note import Note
from .refs import UniformReference
from .apps import *
from .util import *
from .errr import *
from pydantic import BaseModel
from pydantic import BaseModel, Field, computed_field, PastDatetime
from pydantic_core import to_json, from_json
from sqlglot import parse_one, exp, transpile
from sqlglot.executor import execute
from typing import Dict, Iterator, List, Tuple, Iterable
from typing import Optional, Union
from .refs import *


class MutatedEnum(Enum):
    untouched = 'Untouched'
    added = 'Added'
    rename = 'Rename'
    modified = 'Modified'
    modified_unstaged = 'Unstaged Modification (Probably done externally)'
    deleted = 'Deleted'
    deleted_unstaged = 'Unstaged Deletion (Probably done externally)'

    @classmethod
    def parse(cls, s: str):
        if '->' in s:
            path, new_path = s[3:].split(' -> ', 1)
        else:
            path = s[3:]

        if s[0] == 'M':
            return path, MutatedEnum.modified
        elif s[1] == 'M':
            # Modified but not staged
            return path, MutatedEnum.modified_unstaged
        elif s[0] == 'A':
            return path, MutatedEnum.added
        elif s[0] == 'D':
            return path, MutatedEnum.deleted
        elif s[0] == 'R':
            return (path, new_path), MutatedEnum.rename
        elif s[1] == 'D':
            return path, MutatedEnum.deleted_unstaged
        else:
            raise NotImplementedError("Unsupported file state")

    @property
    def staged(self):
        return self.name in ('added', 'modified', 'deleted', 'rename')

class StoredThing(StoredBlob):
    data: Union[Note, Account]
    created: Optional[float] = None
    updated: Optional[float] = None
    size: Optional[int] = None

    @property
    def html_title(self):
        return f'<span class="title">{self.data.icon} {self.data.title}</span>'

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
    def realise_from_str(cls, base, full_path, json_data):
        end = full_path.replace(base, '').lstrip('/').rstrip('.json')
        try:
            urn = UniformReference.from_path(end)
        except ValueError as ve:
            raise ValueError(f"Error parsing {full_path} into a URN: {ve}")

        try:
            data = from_json(json_data)
            res = ModelFromAttr(data).model_validate(data)
        except ValueError as ve:
            raise ValueError(f"Error reading {full_path}: {ve}")

        if res.namespace != urn.namespace:
            print(base, full_path, res, urn)
            print(f"Odd, {urn.namespace} != {res.namespace} (end={end})")

        return cls(
            urn=urn,
            data=res,
            created=os.path.getctime(full_path),
            updated=os.path.getmtime(full_path),
            size=os.path.getsize(full_path)
        )


class BaseBackend(BaseModel):
    path: str
    name: str
    description: str = ''
    icon: str = '💿'
    prefix: str = Field(default_factory=lambda: ''.join(random.choices(string.ascii_uppercase, k=2)))
    pubkeys: List[str] | None = None
    lfs: bool = True
    _private_key_path: str | None = None
    writable: bool = True

    data: Dict[str, 'WrappedStoredThing'] = Field(default_factory=dict)
    blob: Dict[str, 'WrappedStoredBlob'] = Field(default_factory=dict)

    def read(self, path, mode: str = 'r'):
        if self.pubkeys is None:
            with open(path, mode) as handle:
                return handle.read()
        else:
            if self._private_key_path is None:
                raise Exception("Cannot read, missing a private key for this backend")
            return subprocess_check_output([
                'age', '--decrypt',
                '-i', self._private_key_path,
                path
            ])

    def write(self, full_path: str, data: str | bytes, mode: str = 'w'):
        if not self.writable:
            raise Exception("Read-only store")

        if 'a' in mode:
            raise NotImplementedError()

        if self.pubkeys is None:
            with open(full_path, mode) as handle:
                handle.write(data)
        else:
            with tempfile.NamedTemporaryFile(delete_on_close=False, mode=mode) as fp:
                fp.write(data)
                fp.close()
                args = ['age', '--encrypt']
                for r in self.pubkeys:
                    args.append('-r')
                    args.append(r)

                args.extend(['-o', full_path, fp.name])
                subprocess_check_call(args)
                os.unlink(fp.name)

    def all_things(self) -> Iterable['WrappedStoredThing']:
        yield from self.data.values()

    def pathed(self, path=None):
        possible = []
        for x in self.all_things():
            if x.thing.data.has_tag('page_path'):
                possible.append(x)

        print([x.thing.data.get_tag('page_path') for x in possible])
        if path:
            possible = [x for x  in possible
                        if x.thing.data.get_tag('page_path').val == path]
        return possible

    @property
    def html_title(self):
        home = self.pathed(path='index')
        if len(home) > 0:
            home = home[0]
            return f'<a href="{home.thing.urn.urn}#url">{self.icon} {self.name}: {self.description}</a>'
        return f'{self.icon} {self.name}: {self.description}'

    @property
    def meta_path(self):
        return os.path.join(self.path, 'meta.json')

    def initialise(self):
        self.persist_meta()
        return self.discover_meta(self.path)

    def persist_meta(self):
        if not self.writable:
            raise Exception("Read-only store")

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        data = {
            k: v
            for (k, v)
            in self.model_dump().items()
            if k in ('name', 'description', 'icon', 'pubkeys', 'prefix')
        }

        with open(self.meta_path, 'w') as handle:
            json.dump(data, handle, indent=2)

    @classmethod
    def discover_meta(cls, path):
        meta = os.path.join(path, 'meta.json')
        if os.path.exists(meta):
            with open(meta, 'r') as handle:
                data = json.load(handle)
        else:
            data = {'name': path}
        data['path'] = path

        cls = cls.model_validate(data)
        cls.persist_meta()

        if cls.lfs:
            gitmeta = os.path.join(path, '.gitattributes')
            if not os.path.exists(gitmeta):
                with open(gitmeta, 'w') as handle:
                    handle.write("*.png filter=lfs diff=lfs merge=lfs -text\n")
                    handle.write("*.jpg filter=lfs diff=lfs merge=lfs -text\n")
                    handle.write("*.jpeg filter=lfs diff=lfs merge=lfs -text\n")
                    handle.write("*.webp filter=lfs diff=lfs merge=lfs -text\n")
                    subprocess.check_call(['git', 'add', '.gitattributes'], cwd=path)
        return cls

    @classmethod
    def discover(cls, path):
        return cls.discover_meta(path)

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

    def queryable(self, id, note):
        if self.thing.urn.ext != 'csv':
            return None

        def sanitize(s):
            return re.sub('[^A-Za-z0-9_]', '', s.lower().replace(' ', '_'))

        table_name = sanitize(f"csv_{note.thing.data.title.lower()}__{id}")
        res = []
        columns = []

        with open(self.full_path) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                if not columns:
                    columns = [sanitize(k) for k in row.keys()]
                clean = {sanitize(k): v for (k, v) in row.items()}
                res.append(clean)

        return (table_name, columns, res)


    @computed_field
    @property
    def relative_path(self) -> str:
        return self.thing.urn.path

    @computed_field
    @property
    def ext(self) -> str:
        if '.' in self.thing.urn.path:
            return self.thing.urn.path[self.thing.urn.path.rindex('.') + 1:].lower()
        return 'dat'

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
            for r in res:
                if r.backend == self.backend:
                    return r
            return res[0]
        return None

    @property
    def relative_path(self) -> str:
        return self.thing.relative_path

    @property
    def full_path(self) -> str:
        return os.path.join(self.backend.path, self.thing.relative_path)

    def clean_dict(self, oe: 'OverlayEngine', template=None):
        d = self.thing.data.model_dump()
        d['id'] = self.thing.urn.ident
        d['urn'] = self.thing.urn.urn
        d['url'] = f"{self.thing.urn.urn}#url"
        d['backend'] = self.backend.name
        d['created'] = self.thing.data.created
        d['updated'] = self.thing.data.updated
        d['system'] = self.thing.data.type in ('template', )
        d['blurb'] = self.thing.data.blurb

        for k in ('contents', 'attachments', 'tags', 'tags_v2'):
            if k in d:
                del d[k]

        # TODO: shadowing?
        for tag in self.thing.data.get_tags():
            vv = tag.val
            if isinstance(vv, datetime.datetime):
                d[tag.key] = vv.strftime('%Y-%m-%dT%H:%M:%S')
            elif isinstance(vv, list):
                d[tag.key] = ', '.join(map(str, vv))
            else:
                d[tag.key] = vv

        if isinstance(self.thing.data, Template):
            del d['template_tags_v2']
        #     for tag in self.thing.data.template_tags_v2:
        #         vv = tag.model_dump()
        #         d[tag.key] = vv

        # TODO: web+penemure: also works as a prefix instead of #url as a suffix.
        d['title'] = f'<a href="{self.thing.urn.urn}#url">{self.thing.html_title}</a>'
        d['title_plain'] = f'{self.thing.txt_title}'
        d['title_txt'] = f'{self.thing.data.title}'
        #d['contributors'] = self.thing.data.get_contributors(oe)
        d['final_ancestor_titles'] = []

        if d['parents'] is not None and len(d['parents']) > 0:
            d['parents'] = ' '.join([x.urn for x in self.thing.data.get_parents()])
            try:
                d['parent_first_title'] = oe.find_thing(self.thing.data.parents[0].urn).thing.data.title
            except (KeyError, TypeError):
                d['parent_first_title'] = None

        else:
            d['parents'] = None
            d['parent_first_title'] = None

        ancestors = []
        for ancestor_chain in oe.get_lineage(self):
            if len(ancestor_chain) > 0:
                try:
                    thing = oe.find_thing(ancestor_chain[-1]).thing.data.title
                    d['final_ancestor_titles'].append(thing)
                except KeyError:
                    thing = ancestor_chain[-1]
                    d['final_ancestor_titles'].append(thing.urn)

            for thing in ancestor_chain:
                ancestors.append(thing.urn)
        d['ancestors'] = ' '.join(set(ancestors))
        d['final_ancestor_titles'] = ', '.join(set(d['final_ancestor_titles']))


        for k, v in d.items():
            if isinstance(v, list):
                raise Exception(f"Could not parse {k} as it is {type(v)}: {v}. {self}")
        return d



class GitJsonFilesBackend(BaseBackend):
    last_update: Optional[PastDatetime] = None
    latest_commit: Optional[str] = None

    @classmethod
    def discover(cls, path):
        data = cls.discover_meta(path)
        commit, commitdate = subprocess_check_output([
            'git', 'log', '-n', '1', '--format=%H %at',
        ], cwd=path).decode('utf-8').strip().split(' ')
        data.latest_commit = commit
        data.last_update = datetime.datetime.fromtimestamp(int(commitdate))
        return data

    def sync(self, log_fn):
        if self.last_update is not None:
            pass # todo logic to not push/pull too frequently

        # TODO: replace with git status -s ?
        mods = self.get_backend_modifications().values()
        if any([m.staged for m in mods]):
            log_fn(f'git.sync.{self.name}', f'git commit -m "automatic {self.name}" cwd={self.path}"')
            yield from subprocess_check_output(['git', 'commit', '-m', f'automatic {self.name}'], cwd=self.path).decode('utf-8').split('\n')
            

        log_fn(f'git.sync.{self.name}', f'git pull --rebase cwd={self.path}"')
        yield from subprocess_check_output(['git', 'pull', '--rebase'], cwd=self.path).decode('utf-8').split('\n')

        # no point in pushing if nothing's changed.
        if any([m.staged for m in mods]):
            log_fn(f'git.sync.{self.name}', f'git push cwd={self.path}"')
            yield from subprocess_check_output(['git', 'push'], cwd=self.path).decode('utf-8').split('\n')

    def save_item(self, stored_thing: StoredThing, fsync=True):
        """Save updates to an existing file."""
        if stored_thing.identifier not in self.data:
            state = MutatedEnum.added
        else:
            state = MutatedEnum.modified
        self.data[stored_thing.identifier.ident] = WrappedStoredThing(thing=stored_thing, backend=self, state=state)


        full_path = os.path.join(self.path, stored_thing.relative_path)
        print(f'Saving to {full_path}')
        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        if not stored_thing.data.model_has_changed:
            print("Writing this despite no changes")

        self.write(full_path, to_json(stored_thing.data, indent=2), mode='wb')

        stored_thing.data.model_reset_changed()

        subprocess_check_call(['git', 'add', rebase_path(full_path, self.path)], cwd=self.path)

    def save_blob(self, stored_blob: StoredBlob, fsync=True, data: Optional[bytes]=None):
        """Save updates to an existing file."""
        if stored_blob.identifier not in self.data:
            state = MutatedEnum.added
        else:
            state = MutatedEnum.modified
        self.blob[stored_blob.identifier.ident] = WrappedStoredBlob(thing=stored_blob, backend=self, state=state)

        full_path = os.path.join(self.path, stored_blob.relative_path)
        if not os.path.exists(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))

        # stored_blob.data.persist_attachments(os.path.join(self.path, 'file',
        # 'blob'))
        # TODO: do we need to write to the blob at all??
        if data:
            self.write(full_path, data, 'wb')
        else:
            subprocess_check_call(['touch', full_path], cwd=self.path)

        stored_blob.refresh_meta(full_path)
        subprocess_check_call(['git', 'add', rebase_path(full_path, self.path)], cwd=self.path)

        return self.blob[stored_blob.identifier.ident]

    def remove_item(self, stored_thing: StoredThing, fsync=False):
        del self.data[stored_thing.identifier.ident]
        full_path = os.path.join(self.path, stored_thing.relative_path)
        os.unlink(full_path)
        subprocess_check_call(['git', 'rm', rebase_path(full_path, self.path)], cwd=self.path)

    def save(self, fsync=True):
        for v in self.data.values():
            if isinstance(v, StoredThing):
                self.save_item(v, fsync=fsync)
            elif isinstance(v, StoredBlob):
                self.save_blob(v, fsync=fsync)

    def find(self, identifier: UniformReference) -> WrappedStoredThing:
        # import inspect
        # for frame in inspect.stack():
        #     print(f'      {frame.filename}:{frame.lineno}:{frame.function}')

        if identifier.ident in self.data:
            return self.data[identifier.ident]

        raise KeyError(f"[Note] Could not find {identifier.ident}")

    def find_s(self, identifier: str) -> WrappedStoredThing:
        ufr = UniformReference.from_string(identifier)
        return self.find(ufr)

    def find_blob(self, identifier: UniformReference) -> WrappedStoredBlob:
        if identifier.ident in self.blob:
            return self.blob[identifier.ident]

        # for ident, ref in self.blob.items():
        #     if ident.ident == identifier.ident:
        #         return ref
        raise KeyError(f"[Blob] Could not find {identifier.ident}")

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

    def store_blob(self, file_data: bytes, ext:str = 'bin'):
            m = hashlib.sha256()
            m.update(file_data)
            file_hash = m.hexdigest()
            fn = f"{file_hash}.{ext.lstrip('.')}"
            att_urn = UniformReference(app='file', namespace='blob', ident=fn)
            att_blob = StoredBlob(urn=att_urn)
            self.save_blob(att_blob, fsync=False, data=file_data)
            return att_urn

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
        # Ignore untracked files
        statuses = [x for x in statuses if x[0:2] != '??']
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
                try:
                    st = StoredBlob.realise_from_path(self.path, path)
                    self.blob[st.identifier.ident] = WrappedStoredBlob(thing=st, backend=self, state=status)
                except ValueError as ve:
                    print(f"Error loading: {path} {ve}")
            else:
                try:
                    json_data = self.read(path)
                    st = StoredThing.realise_from_str(self.path, path, json_data)
                    self.data[st.identifier.ident] = WrappedStoredThing(thing=st, backend=self, state=status)
                except ValueError as ve:
                    print(f"Error loading: {path} {ve}")



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
        print(f"Wow, really could not find {identifier}")
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

    def find_thing_safe(self, identifier: (UniformReference | str), safe=False) -> WrappedStoredThing | None:
        try:
            return self.find(identifier=identifier)
        except KeyError:
            return None

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

    def all(self, ordering=None) -> list[WrappedStoredThing] | Iterable[WrappedStoredThing]:
        # t = [self.find(k) for k in self.keys()]
        t = self.values()
        if ordering is not None:
            if ordering.startswith('-'):
                t = sorted(t, key=lambda x: getattr(x.thing.data, ordering[1:]))
                t = t[::-1]
            else:
                t = sorted(t, key=lambda x: getattr(x.thing.data, ordering))
        return t

    def all_things(self, ordering=None) -> list[WrappedStoredThing]:
        return [x for x in self.all(ordering=ordering)]

    def all_pathed_pages(self) -> list[WrappedStoredThing]:
        r = []
        for b in self.backends:
            for x in b.all_things():
                if x.thing.data.has_tag('page_path'):
                    r.append(x)
        return r

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

    def values(self) -> Iterable[WrappedStoredThing]:
        for backend in self.backends:
            yield from backend.data.values()

    def add(self, note: Note, backend: Optional[GitJsonFilesBackend]=None, fsync=False, urn=None) -> WrappedStoredThing:
        if urn is None:
            urn = UniformReference(app=note.type, namespace=note.namespace)
        st = StoredThing(data=note, urn=urn)
        be = self.save_item(st, backend=backend, fsync=fsync)
        return WrappedStoredThing(thing=st, backend=be)

    def save_thing(self, ws: WrappedStoredThing, fsync=False) -> WrappedStoredThing:
        ws.backend.save_item(ws.thing, fsync=fsync)
        return ws

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
        """
        e.g. 

            self.search(type='template', title=type)

        """
        results = []
        custom = None
        if 'custom' in kwargs:
            custom = kwargs['custom']
            del kwargs['custom']

        for st in self.all_things():
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
            results = sorted(results, key=lambda x: x.thing.data.start())
        elif custom == 'not-open-recent':
            results = [x for x in results if not x.thing.data.log_is_closed()]
            results = sorted(results, key=lambda x: x.thing.data.start())
            results = results[-100:]

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
    def group_by(cls, data: list[WrappedStoredThing], key) -> list[tuple[str, list[WrappedStoredThing]]]:
        # not really a class method more of a utility? MOVE?

        def get_created_date(s: WrappedStoredThing) -> str:
            return str(s.thing.data.start('date'))

        groups = []
        data = sorted(data, key=lambda x: x.thing.data.start('unix'))[::-1]
        if key == 'day':
            groups = [(x, list(y)) for (x, y) in itertools.groupby(data, get_created_date)]
        else:
            raise Exception('unimplemented')

        return groups

    @classmethod
    def summarise_groups(cls, data: list[tuple[str, list[WrappedStoredThing]]], method: str) -> Iterator[tuple[dict, list[WrappedStoredThing]]]:
        for key, group in data:
            if method == 'duration':
                calc = sum([x.thing.data.duration().seconds for x in group])
                m0 = min([x.thing.data.start('datetime') for x in group])
                m1 = max([x.thing.data.end('datetime') for x in group])
                yield ({
                    "title": key,
                    "calc": datetime.timedelta(seconds=calc),
                    "bound": m1-m0,
                }, group)

    _cache = None
    _cache_sqlite = None
    _cached_valid_tables = []
    _enable_sqlite = True # os.environ.get('SQLITE', 'false') != 'false'
    def make_a_db(self):
        if self._cache_sqlite is None:
            self._cache_sqlite = sqlite3.connect(":memory:", check_same_thread=False)
            # self._cache_sqlite = sqlite3.connect(".cache.db", check_same_thread=False)

        # Saves less time than I thought. hmm.
        # return self._make_a_db(ensure_present)
        if self._cache is None or any([x.thing.data.model_has_changed for x in self.all_things()]):
            # print("Loading SQL DB")
            res = self._make_a_db()
            # a = time.time()
            self._cache = res
            # a = time.time()
            for table, rows in res.items():
                if len(rows) == 0:
                    continue
                okeys = sorted(rows[0].keys())
                qokeys = [f"'{x}'" for x in okeys]
                qqkeys = ['?'] * len(okeys)
                self._cached_valid_tables.append(table)
                # print(table, rows[0])

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

    def _make_a_db(self):
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


        tables['__attachments__'] = [
            # {'id': 'logo', 'urn': 'urn:penemure:system:logo', 'parent': None, 'parent_title': 'System', 'size': 0}
        ]
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

                if results := blob.queryable(id, note):
                    (name, _, rows) = results
                    tables[name] = rows

        for app in self.apps():
            if app not in tables:
                tables[app] = []

        tables['__backend__'] = []
        for b in self.backends:
            tables['__backend__'].append({
                'id': b.name,
                'name': b.name,
                'title': b.html_title,
                'icon': b.icon,
                'description': b.description,
                'path': b.path,
                'last_commit': b.latest_commit,
                'last_update': b.last_update,
            })

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

        tables = {k: fix_tags(v)
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

    def query(self, query: str, via=None, sql=False) -> GroupedResultSet:
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

        # Build the database
        _ = self.make_a_db()

        # TODO: does not work with CTEs
        tables = [x.this.this for x in res.find_all(exp.Table) 
                  if not x.this.this.startswith('cte_') and f"WITH {x.this.this}" not in res.sql()]
        if any([t not in self._cached_valid_tables for t in tables]):
            raise Exception(f"Query has a mismatch with known tables: requested={tables} all={self._cached_valid_tables}")

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

        # print(groupless_query)
        results = self._cache_sqlite.execute(groupless_query)
        # print(f'Executed query in {time.time() - a}')
        header = [x.split(' AS ')[1] if ' AS ' in x else x for x in selects]
        r = ResultSet.build(header, list(results), has_id=not(sql))
        # r = ResultSet(title=None, header=header, rows=list(results))

        if len(r.rows) == 0:
            return GroupedResultSet(groups=[])

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

    def get_lineage(self, note: WrappedStoredThing): # -> Generator[list[WrappedStoredThing]]:
        res = []
        for x in self._get_lineage(note):
            if x == []:
                yield []
            else:
                yield x[1:]

    def _get_lineage(self, note: WrappedStoredThing, lineage=None, orig: str = "", _depth: int=0): # -> Generator[list[WrappedStoredThing]]:
        if lineage is None:
            lineage = []

        # print(f"{'  ' * _depth}_get_lineage({note.thing.urn.urn}, lineage={lineage})")
        parents = note.thing.data.get_parents()
        if note.thing.urn in lineage:
            yield lineage + [UniformReference(app='system', namespace='lineage', ident='loop')]
        elif _depth > 10:
            yield lineage + [note.thing.urn] #+ ['depth-exceeded']
        elif len(parents) == 0:
            yield lineage + [note.thing.urn] #+ ['orphan']
        else:
            for p_urn in parents[::-1]:
                # print(f"{'  ' * _depth} >{p_urn}")
                if p_urn in lineage:
                    yield lineage + [UniformReference(app='system', namespace='lineage', ident='loop')]
                else:
                    try:
                        p = self.find(p_urn)
                        # print(f"{'  ' * _depth} RET {lineage + [note.thing.urn]}")
                        yield from self._get_lineage(p, lineage=lineage + [note.thing.urn], _depth=_depth + 1)
                    except KeyError:
                        # print(f"{'  ' * _depth} RETZ: {lineage + [p_urn]}")
                        yield lineage + [note.thing.urn] + [p_urn]

    def get_template(self, type):
        res = self.search(type='template', title=type)
        if len(res) > 0:
            return res[0]
        return None
