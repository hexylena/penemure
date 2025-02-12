from penemure.store import GitJsonFilesBackend
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
from penemure.refs import *
import sqlglot
import sys

gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
gb2 = GitJsonFilesBackend.discover('./projects/alt')

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
