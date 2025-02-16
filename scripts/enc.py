from penemure.store import GitJsonFilesBackend, OverlayEngine, StoredThing
from penemure.note import Note, MarkdownBlock
from penemure.refs import UniformReference, UnresolvedReference
from penemure.apps import *
from penemure.main import *
from datetime import datetime
from zoneinfo import ZoneInfo


# REPOS = os.environ.get('REPOS', './sec').split(':')
REPOS = './sec'.split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
for b in backends:
    b._private_key_path = './key.txt'
bos = Penemure(backends=backends)
bos.load()

n = Note(title="Testing")
print(bos.overlayengine.add(n))

bos.save()

for n in bos.overlayengine.all():
    print(n.thing.urn.urn, n.thing.relative_path)
