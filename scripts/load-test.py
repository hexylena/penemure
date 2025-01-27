from boshedron.store import *
from boshedron.main import *
from boshedron.apps import *
from boshedron.note import *
from boshedron.tags import *
import sqlglot
import sys


st = StoredThing.realise_from_path(sys.argv[1], sys.argv[2])
print(to_json(st.data, indent=2).decode('utf-8'))
