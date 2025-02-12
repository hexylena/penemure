from penemure.store import *
from penemure.main import *
from penemure.apps import *
from penemure.note import *
from penemure.tags import *
import sqlglot
import sys


st = StoredThing.realise_from_path(sys.argv[1], sys.argv[2])
print(to_json(st.data, indent=2).decode('utf-8'))
