serve:
	find *.go | entr -r bash -c "date && go fmt; go build && ./pm list"

fmt:
	go fmt github.com/hexylena/pm github.com/hexylena/pm/tui github.com/hexylena/pm/cmd github.com/hexylena/pm/models
