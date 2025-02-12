from penemure.store import *
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import sqlglot
import sys

gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
gb2 = GitJsonFilesBackend.discover('./pub')

bos = Penemure(backends=[gb1, gb2])
bos.load()

(parent, child) = sys.argv[1:]
p = bos.overlayengine.find(parent)
c = bos.overlayengine.find(child)

if p is None or c is None:
    sys.exit(1)

if not (isinstance(p, WrappedStored) and isinstance(c, WrappedStored)):
    print(type(p), type(c))
    print("One of these is a stored blob")
    sys.exit(1)

p = narrow_thing(p)
c = narrow_thing(c)

if c.thing.data.parents is None:
    c.thing.data.parents = [p.thing.urn]
else:
    c.thing.data.parents.append(p.thing.urn)

bos.overlayengine.save(fsync=False)

print(c.thing.data)
