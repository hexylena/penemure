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

def f(w, s):
    return f'{str(s):{w}s}'

res = bos.overlayengine.query(sys.argv[1], sql=True)
if res is None:
    sys.exit(1)

colwidth = [20] * (len(res.groups[0].rows) + 30)

for g in res.groups:
    for i, v in enumerate(g.header):
        if len(str(v)) > colwidth[i]:
            colwidth[i] = len(str(v))
    for r in g.rows:
        for i, v in enumerate(r):
            if len(str(v)) > colwidth[i]:
                colwidth[i] = len(str(v))

for g in res.groups:
    print(f'==== {g.title} ====')
    print(' | '.join([f(c, v) for (c, v) in zip(colwidth, g.header)]))
    print(' | '.join([f(c, type(v)) for (c, v) in zip(colwidth, g.rows[0])]))
    for r in g.rows:
        print(' | '.join([f(c, v) for (c, v) in zip(colwidth, r)]))
