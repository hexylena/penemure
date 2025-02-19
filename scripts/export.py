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

ASSETS = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '..', 'assets', 'data', '*.json')
data = {}
for k in glob.glob(ASSETS):
    f = os.path.basename(k).replace('.json', '')
    with open(k, 'r') as handle:
        data[f] = json.load(handle)

pen = Penemure(backends=backends, title=args.title, description=args.desc, data=data)
oe = pen.overlayengine
oe.load()
pen.export(args.output, format=args.format, prefix=args.prefix)
