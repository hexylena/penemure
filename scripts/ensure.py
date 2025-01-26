from boshedron.store import *
from boshedron.main import *
from boshedron.apps import *
from boshedron.note import *
from boshedron.tags import *
from boshedron.util import *
from zoneinfo import ZoneInfo

import sqlglot
import sys

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub').split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
bos = Boshedron(backends=backends)
bos.load()

for b in bos.backends:
    for k, v in b.data.items():
        # print(k)
        if not isinstance(v, StoredThing):
            continue

        # print(v.created,v.updated, v.data.created, v.data.updated, )
        v.data.created = v.data.created.replace(tzinfo=ZoneInfo("UTC"))
        v.data.updated = v.data.updated.replace(tzinfo=ZoneInfo("UTC"))
        # for x in (v.data.contents or []):
        #     print('\t', x.created, x.updated)
    b.save(fsync=False)
