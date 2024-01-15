serve:
	find *.go */*.go projects/ templates/ | entr -r bash -c "date && go fmt; go build && ./pm export"

list_go_files:
	go list -json ./... | jq '[.Dir, .GoFiles] | .[0] + "/" + .[1][] '

fmt:
	go fmt $$(go list ./...)
