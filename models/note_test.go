package models

import (
	// "fmt"
	"testing"
)

func fieldTest(c int, t *testing.T, field string, expected string) {
	if field != expected {
		t.Errorf("[c%d] o:«%s» != e:«%s»", c, field, expected)
	}
}

func TestGetL(t *testing.T) {
	n := Note{
		NoteId: "1111-2222-3333-4444",
		Title:  "test",
		Type:   "note",
		Meta: []*Meta{
			&Meta{"icon", "icon", "🚦", "🚦"},
			&Meta{"tags", "Tags", []string{"a", "b"}, "🚦"},
		},
	}

	fieldTest(1, t, n.GetS("icon"), "🚦")
	tags := n.GetL("Tags")
	fieldTest(2, t, tags[0], "a")
	fieldTest(3, t, tags[1], "b")
}
