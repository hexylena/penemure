from penemure.store import GitJsonFilesBackend
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import multiprocessing
import sqlglot
import sys

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub').split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]

def sync(b):
    print(b.sync())

with multiprocessing.Pool(4) as p:
    p.map(sync, backends, chunksize=1)
