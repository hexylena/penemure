from boshedron.apps import *
from boshedron.main import *
import sys


backends = [GitJsonFilesBackend.discover(x) for x in sys.argv[1:]]
bos = Boshedron(backends=backends)
oe = bos.overlayengine
oe.load()
bos.export("export2")
