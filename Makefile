watch:
	find assets/index.scss boshedron/templates -type f | $(MAKE) serve

serve: assets/bootstrap.css
	find boshedron/templates -type f | entr -r fastapi dev server.py

assets/bootstrap.css: assets/index.scss
	./node_modules/.bin/sass --quiet --style compressed assets/index.scss assets/bootstrap.css

export:
	python scripts/export.py pub
