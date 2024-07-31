package md

import (
	// "errors"
	"strings"
	// "fmt"
	"testing"
)

func TestBlock2(t *testing.T) {
	props := map[string]string{}
	b1 := Block{
		Id:         "1",
		Type:       "markdown",
		Properties: props,
		Content:    "# Heading 1",
		Children:   []*Block{},
	}
	if strings.TrimSpace(b1.Md()) != "# Heading 1" {
		t.Errorf("o:«%s» != e:«# Heading 1»", b1.Md())
	}
	if strings.TrimSpace(b1.Html()) != "<h1 id=\"heading-1\">Heading 1</h1>" {
		t.Errorf("o:«%s» != e:«<h1 id=\"heading-1\">Heading</h1>»", b1.Html())
	}
}

const headers = `# h1
## h2
### h3
#### h4
##### h5
###### h6
`
const headers_html = `<h1 id="h1">h1</h1>
<h2 id="h2">h2</h2>
<h3 id="h3">h3</h3>
<h4 id="h4">h4</h4>
<h5 id="h5">h5</h5>
<h6 id="h6">h6</h6>
`

func TestParseHeaders(t *testing.T) {
	blocks := MdToBlocks2([]byte(headers))
	if len(blocks) != 6 {
		t.Errorf("o:«%d» != e:«6»", len(blocks))
	}

	out_html := ""
	for _, b := range blocks {
		out_html += b.Html()
	}
	out_html = strings.TrimSpace(out_html)
	if out_html != strings.TrimSpace(headers_html) {
		t.Errorf("o:«%s» != e:«%s»", out_html, headers_html)
	}

	out_md := ""
	for _, b := range blocks {
		out_md += b.Md()
	}

	if out_md != headers {
		t.Errorf("o:«%s» != e:«%s»", out_md, headers)
	}
}

const doc = `# h1

testing [a link](https://example.com)

## h2

an ![alt](https://example.com/image.png)

### h3
#### h4
##### h5
###### h6
`

// func TestParseDoc(t *testing.T) {
// 	blocks := MdToBlocks2([]byte(doc))
//
// 	out_html := ""
// 	for _, b := range blocks {
// 		out_html += b.Html()
// 	}
// 	out_html = strings.TrimSpace(out_html)
// 	if out_html != strings.TrimSpace(headers_html) {
// 		t.Errorf("o:«%s» != e:«%s»", out_html, headers_html)
// 	}
//
// 	out_md := ""
// 	for _, b := range blocks {
// 		out_md += b.Md()
// 	}
//
// 	if out_md != headers {
// 		t.Errorf("o:«%s» != e:«%s»", out_md, headers)
// 	}
// }
