from penemure.store import GitJsonFilesBackend
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import sqlglot
import sys

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub').split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
pen = Penemure(backends=backends)
pen.load()

# me = pen.overlayengine.search(type='account', namespace=None)[0]

def f(w, s):
    return f'{str(s):{w}s}'

res = pen.overlayengine.query(sys.argv[1], sql=True)
print(res)
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
