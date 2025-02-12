from penemure.store import GitJsonFilesBackend, OverlayEngine, StoredThing
from penemure.note import Note, MarkdownBlock
from penemure.refs import UniformReference, UnresolvedReference
from penemure.apps import *
from penemure.main import *
from datetime import datetime
from zoneinfo import ZoneInfo

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub').split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
bos = Penemure(backends=backends)
bos.load()

for blob in bos.overlayengine.all_blobs():
    print(blob.thing.urn)
    print(blob.full_path)
