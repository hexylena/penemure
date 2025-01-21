from boshedron.store import *
from boshedron.main import *
from boshedron.apps import *
from boshedron.note import *
from boshedron.tags import *
import sqlglot
import sys

gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
gb2 = GitJsonFilesBackend.discover('./projects/alt')

bos = Boshedron(backends=[gb1, gb2])
bos.load()

for urn in sys.argv[1:]:
    p = bos.overlayengine.find(urn)
    if p is None:
        print(f"Could not find {p}")

    p.thing.data.touch()
bos.save()
