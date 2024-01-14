package models

type BlockType string

const (
	H1 BlockType = "h1"
	H2 BlockType = "h2"
	H3 BlockType = "h3"
	P  BlockType = "p"
)

type Block struct {
	Contents string    `json:"contents"`
	Type     BlockType `json:"type"`
}

func (b *Block) ToHtml() string {
	switch b.Type {
	case H1:
		return "<h1>" + b.Contents + "</h1>"
	case H2:
		return "<h2>" + b.Contents + "</h2>"
	case H3:
		return "<h3>" + b.Contents + "</h3>"
	case P:
		return "<p>" + b.Contents + "</p>"
	}
	return ""
}

func (b *Block) ToHtml3() string {
	switch b.Type {
	case H1:
		return "<h3>" + b.Contents + "</h3>"
	case H2:
		return "<h4>" + b.Contents + "</h4>"
	case H3:
		return "<h5>" + b.Contents + "</h5>"
	default:
		return b.ToHtml()
	}
	return ""
}
