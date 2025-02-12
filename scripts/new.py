from penemure.store import GitJsonFilesBackend
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import sqlglot
import sys

gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
gb2 = GitJsonFilesBackend.discover('./projects/alt')

bos = Penemure(backends=[gb1, gb2])
bos.load()

n = Project(title="Testing")
bos.overlayengine.add(n)

bos.save()
