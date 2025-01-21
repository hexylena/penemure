from boshedron.store import GitJsonFilesBackend
import subprocess
from boshedron.main import *
from boshedron.apps import *
from boshedron.note import *
from boshedron.tags import *
import sqlglot
import sys

gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
gb2 = GitJsonFilesBackend.discover('./pub')
bos = Boshedron(backends=[gb1, gb2])
bos.load()

contents = subprocess.check_output(['xsel', '-b']).decode('utf-8')

res = Note(title=sys.argv[1], contents=[MarkdownBlock(contents=contents, author=UniformReference.from_string('urn:boshedron:account:hexylena'), type='markdown')])

ws = bos.overlayengine.add(res, backend=gb2)
print(ws.thing.urn.urn)
