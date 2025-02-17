watch:
	find server.py assets/*.scss penemure -type f | entr -r $(MAKE) serve

watch-css:
	./node_modules/.bin/sass --quiet --style compressed assets/index.scss assets/bootstrap.css --watch

serve: assets/bootstrap.css assets/print-mono.css
	fastapi run server.py

assets/bootstrap.css: assets/index.scss
	./node_modules/.bin/sass --quiet --style compressed assets/index.scss assets/bootstrap.css

assets/print-mono.css: assets/print-mono.scss
	./node_modules/.bin/sass --quiet --style compressed assets/print-mono.scss assets/print-mono.css

export:
	python scripts/export.py pub
