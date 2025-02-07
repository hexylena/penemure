from boshedron.apps import *
from boshedron.main import *
import sys
import argparse

parser = argparse.ArgumentParser(
                    prog='BOSHEDRON',
                    description='Export')
parser.add_argument('repo', type=str, nargs='+')
parser.add_argument('-o', '--output', type=str, required=False, default='html')
args = parser.parse_args()

backends = [GitJsonFilesBackend.discover(x) for x in args.repo]
bos = Boshedron(backends=backends)
oe = bos.overlayengine
oe.load()
bos.export(args.output)
