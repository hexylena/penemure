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

me = bos.overlayengine.search(type='account', namespace=None)[0]
# t = IconTag(value="👩‍🚒")
# me.data.add_tag(t, unique=True)
# index = bos.overlayengine.search(type='page')[0]

log = Log(title="Working on the project manager")
log.add_tag(DateTimeTag(title='Start Date'))

bos.overlayengine.add(log)

# print(index.data.tags)
# t = TemplateTag(value="plain.html")
# index.data.add_tag(t, unique=True)
# print("Getting tags")
# print(index.data.get_tag(typ='template'))
# print(index.data.get_contributors(bos.overlayengine))
#
# task1 = bos.overlayengine.search(type='task')[0]
# task2 = bos.overlayengine.search(type='task')[1]
# task1.data.add_tag(LifecycleTag(value='done'), unique=True)
# task2.data.add_tag(LifecycleTag(value='in-progress'), unique=True)
# print(bos.overlayengine.get_path(task1))
# print(bos.overlayengine.get_path(task2))


# p = Page(title="Home", page_path="page/index")
# p.contents = [
#     MarkdownBlock(author=me.urn, contents="Testing blocks"),
#     MarkdownBlock(author=me.urn, contents="select title, created from project", type="query-table"),
#     MarkdownBlock(author=me.urn, contents="select title, created from task", type="query-kanban"),
# ]


bos.save()

# res = bos.overlayengine.query(sys.argv[1])
# if isinstance(res, sqlglot.executor.table.Table):
#     print(res)
# else:
#     for k, v in res.items():
#         print(f'=== {k} ===')
#         for v in v:
#             print(' '.join(v))
