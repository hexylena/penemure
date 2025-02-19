watch:
	find server.py assets/*.scss penemure -type f | entr -r $(MAKE) serve

watch-css:
	./node_modules/.bin/sass --quiet --style compressed assets/index.scss assets/bootstrap.css --watch

serve: assets/bootstrap.css assets/print-mono.css assets/data/phosphor.json
	fastapi run server.py

assets/bootstrap.css: assets/index.scss
	./node_modules/.bin/sass --quiet --style compressed assets/index.scss assets/bootstrap.css

assets/print-mono.css: assets/print-mono.scss
	./node_modules/.bin/sass --quiet --style compressed assets/print-mono.scss assets/print-mono.css

assets/data/phosphor.json: node_modules/@phosphor-icons/web/src/regular/selection.json
	cat node_modules/@phosphor-icons/web/src/regular/selection.json | jq '{"meta": .metadata, "icons": [.icons[] | {"id": (.properties.name | split(", "))[0], "tags": (.properties.name | split(", "))}]}' > assets/data/phosphor.json

assets/data/healthicons.json: node_modules/healthicons/public/icons/meta-data.json
	cp -Rv assets/../node_modules/healthicons/public/icons/svg/ assets/healthicons/
	cat node_modules/healthicons/public/icons/meta-data.json | jq '{"meta": {"name": "Healthicons"}, "icons": [.[] | {"id": .id, "category": .category, "tags": .tags}]  }' | > assets/data/healthicons.json

export:
	python scripts/export.py pub
