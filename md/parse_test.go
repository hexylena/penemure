package md

//
// import (
// 	// "fmt"
// 	"testing"
// )
//
// var headings = []byte(`# Sub1
//
// ## Sub2
//
// ### Sub3
//
// #### FAIL
// `)

// func TestParseHeadings(t *testing.T) {
// 	block := MdToBlocks(headings)
// 	// fmt.Println(block[0])
// 	if block[0].Type != H1 {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Type, "H1")
// 	}
// 	if block[0].Contents != "Sub1" {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Contents, "Sub1")
// 	}
//
// 	if block[1].Type != H2 {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Type, "H2")
// 	}
// 	if block[1].Contents != "Sub2" {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Contents, "Sub2")
// 	}
//
// 	if block[2].Type != H3 {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Type, "H3")
// 	}
// 	if block[2].Contents != "Sub3" {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Contents, "Sub3")
// 	}
//
// 	if block[3].Type != H3 {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Type, "H3")
// 	}
// 	if block[3].Contents != "FAIL" {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Contents, "FAIL")
// 	}
// 	// fmt.Println(block[1])
// }
//
// var mds2 = []byte(`This is a **bold** text and _italic_ text.
//
// https://google.com
//
// [testing](https://google.com)
//
// № Some more texting
// `)
//
// func TestParseBody(t *testing.T) {
// 	block := MdToBlocks(mds2)
// 	// fmt.Println(block)
//
// 	if block[0].Type != P {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Type, "P")
// 	}
// 	if block[0].Contents != "This is a **bold** text and _italic_ text." {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Contents, "This is a bold text and italic text.")
// 	}
//
// 	if block[1].Type != P {
// 		t.Errorf("o:«%s» != e:«%s»", block[1].Type, "P")
// 	}
// 	if block[1].Contents != "[https://google.com](https://google.com)" {
// 		t.Errorf("o:«%s» != e:«%s»", block[1].Contents, "https://google.com")
// 	}
//
// 	if block[2].Type != P {
// 		t.Errorf("o:«%s» != e:«%s»", block[2].Type, "P")
// 	}
// 	if block[2].Contents != "[testing](https://google.com)" {
// 		t.Errorf("o:«%s» != e:«%s»", block[2].Contents, "https://google.com")
// 	}
//
// 	if block[3].Type != P {
// 		t.Errorf("o:«%s» != e:«%s»", block[3].Type, "P")
// 	}
// 	if block[3].Contents != "№ Some more texting" {
// 		t.Errorf("o:«%s» != e:«%s»", block[3].Contents, "№ Some more texting")
// 	}
// }
//
// var mds3 = []byte(`ol
//
// 1. item 1
// 2. item 2
//
// ul
//
// - item 1
// - item 2
//
// ![asdf](http://example.com/image.png)
// `)
//
// func TestParseList(t *testing.T) {
// 	block := MdToBlocks(mds3)
// 	// fmt.Println(block)
//
// 	if block[0].Type != P {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Type, "P")
// 	}
// 	if block[0].Contents != "ol" {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Contents, "ol")
// 	}
//
// 	if block[1].Type != OL {
// 		t.Errorf("o:«%s» != e:«%s»", block[1].Type, "OL")
// 	}
// 	if len(block[1].Contents.([]string)) != 2 {
// 		t.Errorf("o:«%d» != e:«%d»", len(block[1].Contents.([]string)), 2)
// 	}
// 	if block[1].Contents.([]string)[0] != "item 1" {
// 		t.Errorf("o:«%s» != e:«%s»", block[1].Contents.([]string)[0], "item 1")
// 	}
// 	if block[1].Contents.([]string)[1] != "item 2" {
// 		t.Errorf("o:«%s» != e:«%s»", block[1].Contents.([]string)[1], "item 2")
// 	}
//
// 	if block[2].Type != P {
// 		t.Errorf("o:«%s» != e:«%s»", block[2].Type, "P")
// 	}
// 	if block[2].Contents != "ul" {
// 		t.Errorf("o:«%s» != e:«%s»", block[2].Contents, "ul")
// 	}
//
// 	if block[3].Type != UL {
// 		t.Errorf("o:«%s» != e:«%s»", block[3].Type, "UL")
// 	}
// 	if len(block[3].Contents.([]string)) != 2 {
// 		t.Errorf("o:«%d» != e:«%d»", len(block[3].Contents.([]string)), 2)
// 	}
// 	if block[3].Contents.([]string)[0] != "item 1" {
// 		t.Errorf("o:«%s» != e:«%s»", block[3].Contents.([]string)[0], "item 1")
// 	}
// 	if block[3].Contents.([]string)[1] != "item 2" {
// 		t.Errorf("o:«%s» != e:«%s»", block[3].Contents.([]string)[1], "item 2")
// 	}
// 	// fmt.Println(block)
//
// 	if block[4].Type != IMG {
// 		t.Errorf("o:«%s» != e:«%s»", block[4].Type, "IMG")
// 	}
//
// 	// TODO: losing the alt text
// 	// fmt.Println(block[4].Contents)
// 	if block[4].Contents != "http://example.com/image.png" {
// 		t.Errorf("o:«%s» != e:«%s»", block[4].Contents, "http://example.com/image.png")
// 	}
// }
//
// var mds4 = []byte("Testing\n\n```go\nfunc main() {\n\tfmt.Println(\"Hello World\")\n}\n```")
//
// func TestParseCode(t *testing.T) {
// 	block := MdToBlocks(mds4)
// 	// fmt.Println(block)
//
// 	if block[0].Type != P {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Type, "P")
// 	}
//
// 	if block[1].Type != CODE {
// 		t.Errorf("o:«%s» != e:«%s»", block[1].Type, "CODE")
// 	}
// 	if block[1].Contents != "```\nfunc main() {\n\tfmt.Println(\"Hello World\")\n}\n```" {
// 		t.Errorf("o:«%s» != e:«%s»", block[1].Contents, "```\nfunc main() {\n\tfmt.Println(\"Hello World\")\n}\n```")
// 	}
// }
//
// var mds5 = []byte(`# printer
// In order to scan
// 1. Press the wifi button
// 1. Switch networks to that network
// 1. It’s not “Canon Print” it’s PRINT” with a Canon Logo, not confusing AT ALL
//
// # Cats
// 50g food per day
// ![](http://placekitten.com/200/300)
// `)
//
// func TestParseMultiple(t *testing.T) {
// 	block := MdToBlocks(mds5)
// 	// fmt.Println(block)
//
// 	if block[0].Type != H1 {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Type, "H1")
// 	}
// 	if block[0].Contents != "printer" {
// 		t.Errorf("o:«%s» != e:«%s»", block[0].Contents, "printer")
// 	}
//
// 	if block[1].Type != P {
// 		t.Errorf("o:«%s» != e:«%s»", block[1].Type, "P")
// 	}
// 	if block[1].Contents != "In order to scan" {
// 		t.Errorf("o:«%s» != e:«%s»", block[1].Contents, "In order to scan")
// 	}
//
// 	if block[2].Type != OL {
// 		t.Errorf("o:«%s» != e:«%s»", block[2].Type, "OL")
// 	}
// 	if len(block[2].Contents.([]string)) != 3 {
// 		t.Errorf("o:«%d» != e:«%d»", len(block[2].Contents.([]string)), 3)
// 	}
// 	if block[2].Contents.([]string)[0] != "Press the wifi button" {
// 		t.Errorf("o:«%s» != e:«%s»", block[2].Contents.([]string)[0], "Press the wifi button")
// 	}
// 	if block[2].Contents.([]string)[1] != "Switch networks to that network" {
// 		t.Errorf("o:«%s» != e:«%s»", block[2].Contents.([]string)[1], "Switch networks to that network")
// 	}
// 	if block[2].Contents.([]string)[2] != "It’s not “Canon Print” it’s PRINT” with a Canon Logo, not confusing AT ALL" {
// 		t.Errorf("o:«%s» != e:«%s»", block[2].Contents.([]string)[2], "It’s not “Canon Print” it’s PRINT” with a Canon Logo, not confusing AT ALL")
// 	}
//
// 	if block[3].Type != H1 {
// 		t.Errorf("o:«%s» != e:«%s»", block[3].Type, "H1")
// 	}
// 	if block[3].Contents != "Cats" {
// 		t.Errorf("o:«%s» != e:«%s»", block[3].Contents, "Cats")
// 	}
//
// 	if block[4].Type != P {
// 		t.Errorf("o:«%s» != e:«%s»", block[4].Type, "P")
// 	}
// 	if block[4].Contents != "50g food per day" {
// 		t.Errorf("o:«%s» != e:«%s»", block[4].Contents, "50g food per day")
// 	}
//
// 	if block[5].Type != IMG {
// 		t.Errorf("o:«%s» != e:«%s»", block[5].Type, "IMG")
// 	}
// 	if block[5].Contents != "http://placekitten.com/200/300" {
// 		t.Errorf("o:«%s» != e:«%s»", block[5].Contents, "http://placekitten.com/200/300")
// 	}
// }
