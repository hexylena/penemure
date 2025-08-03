from penemure.store import GitJsonFilesBackend
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import sqlglot
import sys

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub').split(':')
bos = Penemure.discover(REPOS)
bos.load()


note = bos.overlayengine.search(title='multi-parent-testing')[0]

# def get_lineage(note, oe, lineage=None):
#     parents = note.thing.data.get_parents()
#     a = note.thing.urn.urn
#     if len(parents) == 0:
#         if lineage is not None:
#             yield lineage + [a]
#         else:
#             yield [a]
#     else:
#         for p_urn in parents:
#             p = oe.find(p_urn)
#             if lineage is not None:
#                 yield from get_lineage(p, oe, lineage=lineage + [a])
#             else:
#                 yield from get_lineage(p, oe, lineage=[a])
#
# for path in get_lineage(note, bos.overlayengine):
#     print(path)

bos.save(fsync=False)
