serve:
	find *.go | entr -r bash -c "date && go fmt; go build && ./paliko "
