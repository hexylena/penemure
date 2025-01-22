from boshedron.store import GitJsonFilesBackend
from boshedron.main import *
from boshedron.apps import *
from boshedron.note import *
from boshedron.tags import *
import sqlglot
import sys

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub').split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
for b in backends:
    b.sync()
