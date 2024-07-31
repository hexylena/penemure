package models

import (
	"encoding/json"
	"fmt"
	pmd "github.com/hexylena/pm/md"
	"strings"
	"testing"
)

func fieldTest(c int, t *testing.T, field string, expected string) {
	if field != expected {
		t.Errorf("[c%d] o:«%s» != e:«%s»", c, field, expected)
	}
}

const reference = `{"id":"1111-2222-3333-4444","title":"test","type":"note","parents":null,"blocking":null,"_blocks":[{"contents":"Heading 1","level":"1","type":"heading"},{"contents":"Paragraph 1","type":"paragraph"},{"contents":["List 1","List 2"],"ordered":false,"type":"list"},{"alt_text":"Image 1","type":"image","url":"https://example.com/image.png"},{"type":"horizontal_rule"},{"query":"SELECT * FROM table","type":"table_view"},{"contents":"SELECT * FROM table","lang":"sql","type":"code"},{"contents":"Link 1","type":"link","url":"https://example.com"}],"_tags":[{"type":"icon","title":"icon","value":"🚦","icon":"🚦"},{"type":"tags","title":"Tags","value":["a","b"],"icon":"🚦"}],"created":0,"modified":0,"version":0}`
const minimal = `
{
  "id": "23ab5629-1e89-49b6-b05d-ccf6b36b264c",
  "title": "",
  "type": "",
  "parents": [],
  "blocking": [],
  "_blocks": null,
  "_tags": [],
  "created": 1706176264,
  "modified": 1706176267,
  "version":0
}
`

func TestSerialise(t *testing.T) {
	b1 := &pmd.Heading{Level: "1", Contents: "Heading 1"}
	b2 := &pmd.Paragraph{Contents: "Paragraph 1"}
	b3 := &pmd.List{
		Contents: []string{"List 1", "List 2"},
		Ordered:  false,
	}
	b4 := &pmd.Image{
		Url:     "https://example.com/image.png",
		AltText: "Image 1",
	}
	b5 := &pmd.HorizontalRule{}
	b6 := &pmd.TableView{
		Query: "SELECT * FROM table",
	}
	b7 := &pmd.Code{
		Contents: "SELECT * FROM table",
		Lang:     "sql",
	}
	b8 := &pmd.Link{
		Url:      "https://example.com",
		Contents: "Link 1",
	}

	n := Note{
		NoteId: "1111-2222-3333-4444",
		Title:  "test",
		Type:   "note",
		Meta: []*Meta{
			&Meta{"icon", "icon", "🚦", "🚦"},
			&Meta{"tags", "Tags", []string{"a", "b"}, "🚦"},
		},
		Blocks: []pmd.SyntaxNode{
			b1, b2, b3, b4, b5, b6, b7, b8,
		},
	}

	// Serialise to JSON
	jsonNote, err := json.Marshal(n)
	if err != nil {
		fmt.Println(err)
	}

	if string(jsonNote) != reference {
		t.Errorf("o:«%s» != e:«%s»", string(jsonNote), reference)
	}

	fieldTest(1, t, n.GetS("icon"), "🚦")
	tags := n.GetL("Tags")
	fieldTest(2, t, tags[0], "a")
	fieldTest(3, t, tags[1], "b")
	//
}

func TestDeserialise(t *testing.T) {

	// Deserialise from JSON
	var mmm2 Note
	err := json.Unmarshal([]byte(reference), &mmm2)

	if err != nil {
		fmt.Println(err)
	}
	if mmm2.Title != "test" {
		t.Errorf("o:«%s» != e:«%s»", mmm2.Title, "test")
	}

	if mmm2.Type != "note" {
		t.Errorf("o:«%s» != e:«%s»", mmm2.Type, "note")
	}
	if mmm2.NoteId != "1111-2222-3333-4444" {
		t.Errorf("o:«%s» != e:«%s»", mmm2.NoteId, "1111-2222-3333-4444")
	}

	if mmm2.Blocks[0].(*pmd.Heading).Contents != "Heading 1" {
		t.Errorf("o:«%s» != e:«%s»", mmm2.Blocks[0].(*pmd.Heading).Contents, "Heading 1")
	}
}

func TestDeserialiseSimple(t *testing.T) {

	// Deserialise from JSON
	var mmm2 Note
	err := json.Unmarshal([]byte(minimal), &mmm2)

	if err != nil {
		fmt.Println(err)
	}
	if mmm2.Title != "" {
		t.Errorf("o:«%s» != e:«%s»", mmm2.Title, "")
	}
	for _, thing := range mmm2.Blocks {
		fmt.Println(thing)
	}
}

const reference_markdown = "# Heading 1\n\nParagraph 1\n\n- List 1\n- List 2\n\n\n![Image 1](https://example.com/image.png)\n\n---\n\n```table_view\nSELECT * FROM table\n```\n\n```sql\nSELECT * FROM table\n```\n\n[Link 1](https://example.com)\n\n"

func TestMarkdownRoundtrip(t *testing.T) {
	var n Note
	err := json.Unmarshal([]byte(reference), &n)
	if err != nil {
		fmt.Println(err)
	}

	md := n.RenderMarkdown()
	if md != reference_markdown {
		t.Errorf("o:«%s» != e:«%s»", md, reference_markdown)
	}

	// Ok actual roundtrip
	tmpfile := n.SerialiseToFrontmatterMarkdown()

	// Then parse
	n2 := n.ParseNoteFromMarkdown(tmpfile)
	if err != nil {
		fmt.Println(err)
	}

	jsonNote, err := json.Marshal(n)
	if err != nil {
		fmt.Println(err)
	}

	jsonNote2, err := json.Marshal(n2)
	if err != nil {
		fmt.Println(err)
	}

	ref2 := strings.ReplaceAll(reference, "null", "[]")
	ref2 = strings.ReplaceAll(ref2, "modified\":0", fmt.Sprintf("modified\":%d", n2.ModifiedAt))

	if string(jsonNote) != reference {
		t.Errorf("o:«%s» != e:«%s»", string(jsonNote), reference)
	}
	if string(jsonNote2) != ref2 {
		t.Errorf("o:\n«%s» != e:\n«%s»", string(jsonNote2), ref2)
	}
}
