package md

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	"github.com/gomarkdown/markdown"
	"github.com/gomarkdown/markdown/html"
	"github.com/gomarkdown/markdown/parser"
)

/*

TODO(hexylena)

I think this is the completely wrong structure :D
after reading:
https://www.notion.so/blog/data-model-behind-notion

We should have Blocks, with Contents, blocks all the way down.

Block
  type:Markdown (minus images? not sure how to handle inline properly.)
  type:TableView
  type:Image

Each block has a Contents field which is Block[]

Markdown can have multiple contents (individual markdown blocks)

Is markdown important, then?

## Minimal Set

what's the minimal set of blocks we need? Before we represented every html/md element which was...excessive.

Can we get away with just markdown and 'sql'?

## exmaples ##

Block{
	id "00000000-0000-0000-0000-000000000000",
	type "markdown",
	properties {
		"content": "My first note",
		"tag": "#blessed",
	}
	contents: [
		Block{
			id "00000000-0000-0000-0000-000000000001",
			type "to_do",
			properties {
				"content": "item 1",
				"checked": false,
			}
			contents: [
				Block{
					id "00000000-0000-0000-0000-000000000003",
					type "to_do",
					properties {
						"content": "sub item 1",
						"checked": true,
					}
					contents: [],
				}
			],
		},
		Block{
			id "00000000-0000-0000-0000-000000000002",
			type "to_do",
			properties {
				"content": "item 2",
				"checked": false,
			}
			contents: [],
		},
	]
}


My first note

- [ ] item 1
    - [x] sub item 1
- [ ] item 2




// type Category struct {
//     id int
//     Parent *Category
// }
*/

func mdToHTML(md []byte) []byte {
	// create markdown parser with extensions
	extensions := parser.CommonExtensions | parser.AutoHeadingIDs | parser.NoEmptyLineBeforeBlock
	p := parser.NewWithExtensions(extensions)
	doc := p.Parse(md)

	// create HTML renderer with extensions
	htmlFlags := html.CommonFlags | html.HrefTargetBlank
	opts := html.RendererOptions{Flags: htmlFlags}
	renderer := html.NewRenderer(opts)

	return markdown.Render(doc, renderer)
}

type Block struct {
	Id         string            `json: "id"`
	Type       string            `json: "type"`
	Properties map[string]string `json: "properties"`
	Content    string            `json: "content"`
	Children   []*Block          `json: "children"`
}

func (b *Block) Html() string {
	content := b.Content
	return string(mdToHTML([]byte(content)))
}

func (b *Block) Md() string {
	return b.Content + "\n"
}

type SyntaxNode interface {
	Html() string
	Md() string
	Type() string
	String() string
}

type Heading struct {
	Level    string `json:"level"`
	Contents string `json:"contents"`
}

func (h *Heading) Html() string {
	i, _ := strconv.ParseInt(h.Level, 10, 64)
	i += 2
	return fmt.Sprintf("<h%d>%s</h%d>", i, h.Contents, i)
}

func (h *Heading) Md() string {
	// adjust from h.Level
	i, _ := strconv.ParseInt(h.Level, 10, 64)
	return fmt.Sprintf("%s %s", strings.Repeat("#", int(i)), h.Contents)
}

func (h *Heading) Type() string {
	return "heading"
}

func (h *Heading) MarshalJSON() (b []byte, e error) {
	return json.Marshal(map[string]string{
		"type":     "heading",
		"level":    h.Level,
		"contents": h.Contents,
	})
}

func (s *Heading) String() string {
	return fmt.Sprintf("Sn{%s}: %s", s.Type(), s.Md())
}

type Paragraph struct {
	Contents string `json:"contents"`
}

func (p *Paragraph) Html() string {
	return string(mdToHTML([]byte(p.Contents)))

}

func (p *Paragraph) Md() string {
	return p.Contents
}

func (p *Paragraph) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["contents"] = p.Contents
	m["type"] = "paragraph"
	return json.Marshal(m)
}

func (p *Paragraph) Type() string {
	return "paragraph"
}

func (s *Paragraph) String() string {
	return fmt.Sprintf("Sn{%s}: %s", s.Type(), s.Md())
}

type List struct {
	Contents []string `json:"contents"`
	Ordered  bool     `json:"ordered"`
}

func (l *List) Html() string {
	out := ""
	for _, c := range l.Contents {
		out += "<li>" + c + "</li>"
	}
	if l.Ordered {
		return "<ol>" + out + "</ol>"
	}
	return "<ul>" + out + "</ul>"
}

func (l *List) Md() string {
	out := ""
	for _, c := range l.Contents {
		if l.Ordered {
			out += "1. " + c + "\n"
		} else {
			out += "- " + c + "\n"
		}
	}
	return out
}

func (l *List) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["contents"] = l.Contents
	m["ordered"] = l.Ordered
	m["type"] = "list"
	return json.Marshal(m)
}

func (l *List) Type() string {
	return "list"
}

func (s *List) String() string {
	return fmt.Sprintf("Sn{%s}: %s", s.Type(), s.Md())
}

type Image struct {
	AltText string `json:"alt_text"`
	Url     string `json:"url"`
}

func (i *Image) Html() string {
	return fmt.Sprintf("<img src=\"%s\" alt=\"%s\" />", i.Url, i.AltText)
}

func (i *Image) Md() string {
	return fmt.Sprintf("![%s](%s)", i.AltText, i.Url)
}

func (i *Image) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["alt_text"] = i.AltText
	m["url"] = i.Url
	m["type"] = "image"
	return json.Marshal(m)
}

func (i *Image) Type() string {
	return "image"
}
func (s *Image) String() string {
	return fmt.Sprintf("Sn{%s}: %s", s.Type(), s.Md())
}

type HorizontalRule struct{}

func (h *HorizontalRule) Html() string {
	return "<hr />"
}

func (h *HorizontalRule) Md() string {
	return "---"
}

func (h *HorizontalRule) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["type"] = "horizontal_rule"
	return json.Marshal(m)
}

func (h *HorizontalRule) Type() string {
	return "horizontal_rule"
}
func (s *HorizontalRule) String() string {
	return fmt.Sprintf("Sn{%s}: %s", s.Type(), s.Md())
}

const TABLE_VIEW = "table_view"

type TableView struct {
	Query string `json:"query"`
}

func (t *TableView) Html() string {
	return t.Query
}

func (t *TableView) Md() string {
	return fmt.Sprintf("```%s\n%s\n```", TABLE_VIEW, t.Query)
}

func (t *TableView) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["query"] = t.Query
	m["type"] = TABLE_VIEW
	return json.Marshal(m)
}

func (t *TableView) Type() string {
	return TABLE_VIEW
}
func (s *TableView) String() string {
	return fmt.Sprintf("Sn{%s}: %s", s.Type(), s.Md())
}

type Code struct {
	Lang     string `json:"lang"`
	Contents string `json:"contents"`
}

func (c *Code) Html() string {
	return fmt.Sprintf("<pre><code class=\"language-%s\">%s</code></pre>", c.Lang, c.Contents)
}

func (c *Code) Md() string {
	return fmt.Sprintf("```%s\n%s\n```", c.Lang, c.Contents)
}

func (c *Code) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["lang"] = c.Lang
	m["contents"] = c.Contents
	m["type"] = "code"
	return json.Marshal(m)
}

func (c *Code) Type() string {
	return "code"
}
func (s *Code) String() string {
	return fmt.Sprintf("Sn{%s}: %s", s.Type(), s.Md())
}

type Link struct {
	Url      string `json:"url"`
	Contents string `json:"contents"`
}

func (l *Link) Html() string {
	return fmt.Sprintf("<a href=\"%s\">%s</a>", l.Url, l.Contents)
}

func (l *Link) Md() string {
	return fmt.Sprintf("[%s](%s)", l.Contents, l.Url)
}

func (l *Link) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["url"] = l.Url
	m["contents"] = l.Contents
	m["type"] = "link"
	return json.Marshal(m)
}

func (l *Link) Type() string {
	return "link"
}
func (s *Link) String() string {
	return fmt.Sprintf("Sn{%s}: %s", s.Type(), s.Md())
}

// type BlockType string
// const (
// 	H1       BlockType = "h1"
// 	H2       BlockType = "h2"
// 	H3       BlockType = "h3"
// 	P        BlockType = "p"
// 	OL       BlockType = "ol"
// 	UL       BlockType = "ul"
// 	IMG      BlockType = "img"
// 	HR       BlockType = "hr"
// 	TBL_VIEW BlockType = "tbl_view" // 'Views'
// 	CODE     BlockType = "code"
// 	A       BlockType = "a"
// )

// type Block struct {
// 	Contents any `json:"contents"`
// 	Type BlockType `json:"type"`
// }

type Table struct {
	Header []string   `json:"thead"`
	Body   [][]string `json:"tbody"`
}

func (t *Table) Html() string {
	out := "<table>"
	// Add table header
	out += "<thead><tr>"
	for _, h := range t.Header {
		out += "<th>" + h + "</th>"
	}
	out += "</tr></thead>"

	// Add table body
	out += "<tbody>"
	for _, row := range t.Body {
		out += "<tr>"
		for _, cell := range row {
			out += "<td>" + cell + "</td>"
		}
		out += "</tr>"
	}
	out += "</tbody>"

	out += "</table>"
	return out
}

func (t *Table) Md() string {
	out := "| " + strings.Join(t.Header, " | ") + " |\n"
	out += "| " + strings.Repeat("--- | ", len(t.Header)) + "\n"
	for _, row := range t.Body {
		out += "| " + strings.Join(row, " | ") + " |\n"
	}
	return out
}

func (t *Table) Type() string {
	return "table"
}

func (t *Table) MarshalJSON() ([]byte, error) {
	m := make(map[string]interface{})
	m["thead"] = t.Header
	m["tbody"] = t.Body
	m["type"] = t.Type()
	return json.Marshal(m)
}

func (s *Table) String() string {
	return fmt.Sprintf("Sn{%s}: %s", s.Type(), s.Md())
}
