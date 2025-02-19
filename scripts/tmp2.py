from penemure.store import GitJsonFilesBackend
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import sqlglot
import sys

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub').split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
bos = Penemure(backends=backends)
bos.load()

# me = bos.overlayengine.search(type='account', namespace=None)[0]

print(bos.overlayengine.search(type='account', namespace='gh', username='hexylena'))

print(bos.pkg_file('base.html'))
