from penemure.store import GitJsonFilesBackend
import subprocess
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import sqlglot
import sys

gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
gb2 = GitJsonFilesBackend.discover('./pub')
bos = Penemure(backends=[gb1, gb2])
bos.load()

contents = subprocess.check_output(['xsel', '-b']).decode('utf-8')

res = Note(title=sys.argv[1], contents=[MarkdownBlock(contents=contents, author=UniformReference.from_string('urn:penemure:account:hexylena'), type='markdown')])

ws = bos.overlayengine.add(res, backend=gb2, fsync=False)
print(ws.thing.urn.urn)
