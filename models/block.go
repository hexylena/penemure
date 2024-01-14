package models

import (
	"fmt"
)

type BlockType string

const (
	H1 BlockType = "h1"
	H2 BlockType = "h2"
	H3 BlockType = "h3"
	P  BlockType = "p"
	OL  BlockType = "ol"
	UL  BlockType = "ul"
	IMG BlockType = "img"
)

type Block struct {
	Contents any    `json:"contents"`
	Type     BlockType `json:"type"`
}

func (b *Block) StringContents() string {
	return fmt.Sprint(b.Contents)
}

func (b *Block) ListContents() []string {
	out := []string{}
	for _, c := range b.Contents.([]interface{}) {
		out = append(out, fmt.Sprint(c))
	}
	return out
}

func (b *Block) ToHtml() string {
	switch b.Type {
	case H1:
		return "<h1>" + b.StringContents() + "</h1>"
	case H2:
		return "<h2>" + b.StringContents() + "</h2>"
	case H3:
		return "<h3>" + b.StringContents() + "</h3>"
	case P:
		return "<p>" + b.StringContents() + "</p>"
	case OL:
		out := "<ol>"
		for _, c := range b.ListContents() {
			out += "<li>" + c + "</li>"
		}
		out += "</ol>"
		return out
	case UL:
		out := "<ul>"
		for _, c := range b.ListContents() {
			out += "<li>" + c + "</li>"
		}
		out += "</ul>"
		return out
	case IMG:
		return "<img src=\"" + b.StringContents() + "\" />"
	}
	return ""
}

func (b *Block) ToHtml3() string {
	switch b.Type {
	case H1:
		return "<h3>" + b.StringContents() + "</h3>"
	case H2:
		return "<h4>" + b.StringContents() + "</h4>"
	case H3:
		return "<h5>" + b.StringContents() + "</h5>"
	default:
		return b.ToHtml()
	}
	return ""
}

func (b *Block) ToMarkdown() string {
	switch b.Type {
	case H1:
		return "# " + b.StringContents()
	case H2:
		return "## " + b.StringContents()
	case H3:
		return "### " + b.StringContents()
	case P:
		return b.StringContents()
	case OL:
		out := ""
		for _, c := range b.ListContents() {
			out += "1. " + c + "\n"
		}
		return out
	case UL:
		out := ""
		for _, c := range b.ListContents() {
			out += "- " + c + "\n"
		}
		return out
	case IMG:
		return "![](" + b.StringContents() + ")"
	}
	return b.StringContents()
}
