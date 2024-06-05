expor:
	find *.go */*.go projects/ templates/ | entr -r bash -c "date && go fmt; go build && ./pm export"

serve:
	find *.go */*.go projects/ templates/ | entr -r bash -c "date && go fmt; go build && ./pm serve"

list_go_files:
	go list -json ./... | jq '[.Dir, .GoFiles] | .[0] + "/" + .[1][] '

fmt:
	go fmt $$(go list ./...)
