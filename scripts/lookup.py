from boshedron.store import GitJsonFilesBackend
from boshedron.main import *
from boshedron.apps import *
from boshedron.note import *
from boshedron.tags import *
from boshedron.refs import *
import sqlglot
import sys

gb1 = GitJsonFilesBackend(name='main', path='projects/main')
# gb2 = GitJsonFilesBackend(name='alt', path='./projects/alt')

gb1.load()
for k, v in gb1.data.items():
    print(repr(k))
# bos = Boshedron(backends=[gb1, gb2])
# bos.load()
#
# me = bos.overlayengine.search(type='account', namespace=None)[0]
# index = bos.overlayengine.search(type='page')[0]
#
# urn = UniformReference.from_string(sys.argv[1])
# print(urn)
# print(bos.overlayengine.find(urn))

# task2 = bos.overlayengine.search(type='task')[1]
