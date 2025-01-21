from boshedron.store import GitJsonFilesBackend
from boshedron.main import *
from boshedron.apps import *
from boshedron.note import *
from boshedron.tags import *
import sys

gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
gb2 = GitJsonFilesBackend.discover('./pub')
bos = Boshedron(backends=[gb1, gb2])
bos.load()

(urn, new_backend) = sys.argv[1:]
n = bos.overlayengine.find(urn)

print(repr(n.thing))
print(f"→ is currently stored in {n.backend.name}")
print()
print(f"Available backends: {[b.name for b in bos.backends]}")

new_be = [b for b in bos.backends if b.name == new_backend]
if len(new_be) == 0:
    raise Exception("Could not find backend")

new_be = new_be[0]

print(bos.overlayengine.migrate_backend(n.thing.urn, new_be))
bos.save()
