from penemure.store import GitJsonFilesBackend
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import sys

REPOS = os.environ.get('REPOS', './sec').split(':')
REPOS = './sec'.split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
bos = Penemure(backends=backends, private_key_path='./key.txt')
bos.load()

# n = Note(title="Testing")
# print(bos.overlayengine.add(n))
# bos.save()

for n in bos.overlayengine.all():
    print(n.thing.urn.urn, n.thing.relative_path, n.thing.data.title)
