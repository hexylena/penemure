serve:
	find boshedron/templates -type f | entr -r fastapi dev server.py

export:
	python scripts/export.py pub
