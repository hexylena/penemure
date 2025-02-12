watch:
	$(MAKE) serve

watch-css:
	./node_modules/.bin/sass --quiet --style compressed assets/index.scss assets/bootstrap.css --watch

serve: assets/bootstrap.css
	find penemure -type f | entr -r fastapi run server.py

assets/bootstrap.css: assets/index.scss
	./node_modules/.bin/sass --quiet --style compressed assets/index.scss assets/bootstrap.css

export:
	python scripts/export.py pub
