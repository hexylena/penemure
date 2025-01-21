from boshedron.store import *
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

(parent, child) = sys.argv[1:]
p = bos.overlayengine.find(parent)
c = bos.overlayengine.find(child)

if p is None or c is None:
    sys.exit(1)

if not (isinstance(p, StoredThing) and isinstance(c, StoredThing)):
    print("One of these is a stored blob")
    sys.exit(1)

if c.data.parents is None:
    c.data.parents = [p.urn]
else:
    c.data.parents.append(p.urn)

print(c.data)

# me = bos.overlayengine.search(type='account', namespace=None)[0]
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


bos.save()
