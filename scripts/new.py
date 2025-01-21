from boshedron.store import GitJsonFilesBackend
from boshedron.main import *
from boshedron.apps import *
from boshedron.note import *
from boshedron.tags import *
import sqlglot
import sys

gb1 = GitJsonFilesBackend(name='main', path='projects/main')
gb2 = GitJsonFilesBackend(name='alt', path='./projects/alt')

bos = Boshedron(backends=[gb1, gb2])
bos.load()

n = Project(title="Testing")
bos.overlayengine.add(n)

bos.save()
