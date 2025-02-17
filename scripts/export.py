from penemure.apps import *
from penemure.main import *
import sys
import argparse

parser = argparse.ArgumentParser(
                    prog='PENEMURE',
                    description='Export')
parser.add_argument('repo', type=str, nargs='+')
parser.add_argument('-o', '--output', type=str, required=False, default='_build')
parser.add_argument('-f', '--format', type=str, choices=['md', 'html'], default='html')
parser.add_argument('-p', '--prefix', type=str, default='project-management')

parser.add_argument('-t', '--title', type=str, default='PENEMURE')
parser.add_argument('-d', '--desc', type=str, default='The public example static site generated from notes and issues stored within the penemure system.')
args = parser.parse_args()

backends = [GitJsonFilesBackend.discover(x) for x in args.repo]
pen = Penemure(backends=backends, title=args.title, description=args.desc)
oe = pen.overlayengine
oe.load()
pen.export(args.output, format=args.format, prefix=args.prefix)
