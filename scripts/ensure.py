from penemure.store import *
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
from penemure.util import *
from zoneinfo import ZoneInfo

import sqlglot
import sys

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub').split(':')
bos = Penemure.discover(REPOS)
bos.load()

for b in bos.backends:
    for k, v in b.data.items():
        # print(k)
        if not isinstance(v, StoredThing):
            continue

        print(v.created,v.updated, v.data.created, v.data.updated, )

        v.data.created_unix = v.data.created.timestamp()
        v.data.updated_unix = v.data.updated.timestamp()
        for x in (v.data.contents or []):
            x.created_unix = x.created.timestamp()
            x.updated_unix = x.updated.timestamp()
    b.save(fsync=False)
