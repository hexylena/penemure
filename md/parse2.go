package md

// example for https://blog.kowalczyk.info/article/cxn3/advanced-markdown-processing-in-go.html

import (
	// "os"

	"github.com/gomarkdown/markdown/ast"
	"github.com/gomarkdown/markdown/parser"
	"strings"

	"fmt"
)


func contentToString2(d1 []byte, d2 []byte) string {
	if d1 != nil {
		return string(d1)
	}
	if d2 != nil {
		return string(d2)
	}
	return ""
}

func getContentOrig2(node ast.Node) string {
	if c := node.AsContainer(); c != nil {
		fmt.Println("getContentOrig2", c.Literal, c.Content)
		return contentToString2(c.Literal, c.Content)
	}
	leaf := node.AsLeaf()
	fmt.Println("getContentOrig2Leaf", leaf.Literal, leaf.Content)
	return contentToString2(leaf.Literal, leaf.Content)
}

func parseBlock2(node ast.Node) []Block {
	// nt := getNodeType(node)
	// fmt.Println("parseBlock", nt, node)
	if c := node.AsContainer(); c != nil {
		if len(c.Children) != 1 {
			fmt.Println("strange container with more than one child")
		}
		switch v := node.(type) {
		case *ast.Heading:
			return []Block{
				Block{
					Type: "markdown",
					Content: strings.Repeat("#", int(v.Level)) + " " + getContentOrig2(c.Children[0]),
				},
			}
		case *ast.Paragraph:
			return []Block{
				Block{
					Type: "markdown",
					Content: getContentOrig2(c.Children[0]),
				},
			}
		// case *ast.List:
		// 	// Get list type
		// 	list_contents := []string{}
		// 	for _, n := range c.Children {
		// 		kid := n.AsContainer().Children[0].AsContainer().Children[0]
		// 		list_contents = append(list_contents, getContentOrig(kid))
		// 	}
		// 	return []Block{
		// 		&List{
		// 			Contents: list_contents,
		// 			Ordered:  v.ListFlags&ast.ListTypeOrdered != 0,
		// 		},
		// 	}
		default:
			panic(fmt.Sprintf("Unhandled container type %T", v))
		}
	} else {
		switch v := node.(type) {
		case *ast.CodeBlock:
			_ = v
			// check code type
			if string(v.Info) == TABLE_VIEW {
				return []Block{
					Block{
						Type: "table_view",
						Content: strings.TrimSpace(getContentOrig2(node)),
					},
				}
			} else {
				return []Block{
					Block{
						Type: "table_view",
						Content: strings.TrimSpace(getContentOrig2(node)),
						Properties: map[string]string{
							"lang": string(v.Info),
						},
					},
				}
			}
		case *ast.HorizontalRule:
			return []Block{
				Block{
					Type: "markdown",
					Content: "---",
				},
			}
		default:
			panic(fmt.Sprintf("Unhandled leaf type %T", v))
		}
	}
	panic("Should not reach here ever")
}

func MdToBlocks2(md []byte) []Block {
	// create markdown parser with extensions
	extensions := parser.CommonExtensions | parser.NoEmptyLineBeforeBlock
	p := parser.NewWithExtensions(extensions)
	doc := p.Parse(md)

	out := []Block{}

	for _, node := range doc.GetChildren() {

		// content := getContent(node)
		// typeName := getNodeType(node)
		blocks := parseBlock2(node)
		out = append(out, blocks...)
		// fmt.Println(typeName, content)
	}
	return out
}
