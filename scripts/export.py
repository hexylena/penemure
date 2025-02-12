from penemure.apps import *
from penemure.main import *
import sys
import argparse

parser = argparse.ArgumentParser(
                    prog='BOSHEDRON',
                    description='Export')
parser.add_argument('repo', type=str, nargs='+')
parser.add_argument('-o', '--output', type=str, required=False, default='_build')
parser.add_argument('-f', '--format', type=str, choices=['md', 'html'], default='html')
parser.add_argument('-p', '--prefix', type=str, default='project-management')
args = parser.parse_args()

backends = [GitJsonFilesBackend.discover(x) for x in args.repo]
bos = Boshedron(backends=backends)
oe = bos.overlayengine
oe.load()
bos.export(args.output, format=args.format, prefix=args.prefix)
