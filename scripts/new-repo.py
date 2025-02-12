from penemure.store import GitJsonFilesBackend
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import sqlglot
import sys

import argparse

parser = argparse.ArgumentParser(
                    prog='BOSHEDRON',
                    description='Initialises a new repo')
parser.add_argument('path', type=str)
parser.add_argument('-n', '--name', type=str, required=True)
parser.add_argument('-d', '--description', type=str, required=False, default='')
args = parser.parse_args()


be = GitJsonFilesBackend.new_meta(args.path, args.name, description=args.description)
print(be)

#
# gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
# gb2 = GitJsonFilesBackend.discover('./projects/alt')
#
# bos = Boshedron(backends=[gb1, gb2])
# bos.load()
#
# n = Project(title="Testing")
# bos.overlayengine.add(n)
#
# bos.save()
