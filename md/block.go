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


type SyntaxNode interface {
	Html() string
	Md() string
	Type() string
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

type Paragraph struct {
	Contents string `json:"contents"`
}


func (p *Paragraph) Html() string {
	return fmt.Sprintf("<p>%s</p>", mdToHTML([]byte(p.Contents)))

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
