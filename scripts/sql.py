from boshedron.store import GitJsonFilesBackend
from boshedron.main import *
from boshedron.apps import *
from boshedron.note import *
from boshedron.tags import *
import sqlglot
import sys

gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
gb2 = GitJsonFilesBackend.discover('./projects/alt')

bos = Boshedron(backends=[gb1, gb2])
bos.load()

me = bos.overlayengine.search(type='account', namespace=None)[0]
# index = bos.overlayengine.search(type='page')[0]
# print(index.data.tags)
# t = TemplateTag(value="plain.html")
# index.data.add_tag(t, unique=True)
#
# print("Getting tags")
# print(index.data.get_tag(typ='template'))

# p = Page(title="Home", page_path="page/index")
# p.contents = [
#     MarkdownBlock(author=me.urn, contents="Testing blocks"),
#     MarkdownBlock(author=me.urn, contents="select title, created from project", type="query-table"),
#     MarkdownBlock(author=me.urn, contents="select title, created from task", type="query-kanban"),
# ]
# bos.save()

def f(s):
    return f'{str(s)[0:30]:30s}'

res = bos.overlayengine.query(sys.argv[1], sql=True)
for g in res.groups:
    print(f'==== {g.title} ====')
    
    print(' | '.join(map(f, g.header)))
    for r in g.rows:
        print(' | '.join(map(f, r)))
