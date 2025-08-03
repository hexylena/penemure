from penemure.apps import *
from penemure.main import *


# REPOS = os.environ.get('REPOS', './sec').split(':')
REPOS = './sec'.split(':')
bos = Penemure.discover(REPOS, private_key_path='./key.txt')
bos.load()

# n = Note(title="Testing")
# print(bos.overlayengine.add(n))
# bos.save()

for n in bos.overlayengine.all():
    print(n.thing.urn.urn, n.thing.relative_path, n.thing.data.title)
