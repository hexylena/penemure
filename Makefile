watch:
	find server.py assets/*.scss penemure -type f | entr -r $(MAKE) serve

watch-css:
	./node_modules/.bin/sass --quiet --style compressed assets/index.scss assets/bootstrap.css --watch

serve: assets/bootstrap.css assets/print-mono.css assets/data/phosphor.json assets/favicon.ico assets/favicon@256.png assets/favicon@512.png assets/favicon@1024.png assets/data/healthicons.json
	fastapi run server.py

assets/bootstrap.css: assets/index.scss
	./node_modules/.bin/sass --quiet --style compressed assets/index.scss assets/bootstrap.css

assets/print-mono.css: assets/print-mono.scss
	./node_modules/.bin/sass --quiet --style compressed assets/print-mono.scss assets/print-mono.css

assets/data/phosphor.json: node_modules/@phosphor-icons/web/src/regular/selection.json
	cat node_modules/@phosphor-icons/web/src/regular/selection.json | jq '{"meta": .metadata, "icons": [.icons[] | {"id": (.properties.name | split(", "))[0], "tags": (.properties.name | split(", "))}]}' > assets/data/phosphor.json

assets/data/healthicons.json: node_modules/healthicons/public/icons/meta-data.json
	mkdir -p assets/healthicons/
	rsync -avr assets/../node_modules/healthicons/public/icons/svg/outline/ assets/healthicons/outline/
	rsync -avr assets/../node_modules/healthicons/public/icons/svg/filled/ assets/healthicons/filled/
	cat node_modules/healthicons/public/icons/meta-data.json | jq '{"meta": {"name": "Healthicons", "prefix": "hi"}, "icons": [.[] | {"id": (.path | sub("/"; "-")), "category": .category, "tags": .tags, "path": .path}]  }' > assets/data/healthicons.json

assets/favicon.ico: penemure.png
	magick penemure.png -resize 64x assets/favicon.ico

assets/favicon@256.png: penemure.png
	magick penemure.png -resize 256x assets/favicon@256.png

assets/favicon@512.png: penemure.png
	magick penemure.png -resize 512x assets/favicon@512.png

assets/favicon@1024.png: penemure.png
	magick penemure.png -resize 1024x assets/favicon@1024.png


export:
	python scripts/export.py pub
