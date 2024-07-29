package md

import (
	"encoding/json"
	"errors"
	"fmt"
	"testing"
)

type ColorfulEcosystem struct {
	Title  string       `json:"title"`
	Things []SyntaxNode `json:"things"`
}

func (ce *ColorfulEcosystem) UnmarshalJSON(b []byte) error {
	// First, deserialize everything into a map of map
	var objMap map[string]*json.RawMessage
	err := json.Unmarshal(b, &objMap)
	if err != nil {
		return err
	}

	var rawMessagesForColoredThings []*json.RawMessage
	err = json.Unmarshal(*objMap["things"], &rawMessagesForColoredThings)
	if err != nil {
		return err
	}

	// Must manually deserialise each item
	err = json.Unmarshal(*objMap["title"], &ce.Title)

	// Let's add a place to store our de-serialized Plant and Animal structs
	ce.Things = make([]SyntaxNode, len(rawMessagesForColoredThings))

	var m map[string]interface{}
	for index, rawMessage := range rawMessagesForColoredThings {
		err = json.Unmarshal(*rawMessage, &m)
		if err != nil {
			return err
		}

		// Depending on the type, we can run json.Unmarshal again on the same byte slice
		// But this time, we'll pass in the appropriate struct instead of a map
		if m["type"] == "heading" {
			var p Heading
			err := json.Unmarshal(*rawMessage, &p)
			if err != nil {
				return err
			}
			// After creating our struct, we should save it
			ce.Things[index] = &p
		} else if m["type"] == "paragraph" {
			var a Paragraph
			err := json.Unmarshal(*rawMessage, &a)
			if err != nil {
				return err
			}
			// After creating our struct, we should save it
			ce.Things[index] = &a
		} else if m["type"] == "image" {
			var a Image
			err := json.Unmarshal(*rawMessage, &a)
			if err != nil {
				return err
			}
			ce.Things[index] = &a
		} else if m["type"] == "list" {
			var a List
			err := json.Unmarshal(*rawMessage, &a)
			if err != nil {
				return err
			}
			ce.Things[index] = &a
		} else if m["type"] == "horizontal_rule" {
			var a HorizontalRule
			err := json.Unmarshal(*rawMessage, &a)
			if err != nil {
				return err
			}
			ce.Things[index] = &a
		} else if m["type"] == "table_view" {
			var a TableView
			err := json.Unmarshal(*rawMessage, &a)
			if err != nil {
				return err
			}
			ce.Things[index] = &a
		} else if m["type"] == "code" {
			var a Code
			err := json.Unmarshal(*rawMessage, &a)
			if err != nil {
				return err
			}
			ce.Things[index] = &a
		} else if m["type"] == "link" {
			var a Link
			err := json.Unmarshal(*rawMessage, &a)
			if err != nil {
				return err
			}
			ce.Things[index] = &a
		} else {
			return errors.New(fmt.Sprintf("Unknown type: %s", m["type"]))
		}
	}

	// That's it!  We made it the whole way with no errors, so we can return `nil`
	return nil
}

func TestSerialisation(t *testing.T) {
	b1 := &Heading{Level: "1", Contents: "Heading 1"}
	b2 := &Paragraph{Contents: "Paragraph 1"}
	b3 := &List{
		Contents: []string{"List 1", "List 2"},
		Ordered:  false,
	}
	b4 := &Image{
		Url:     "https://example.com/image.png",
		AltText: "Image 1",
	}
	b5 := &HorizontalRule{}
	b6 := &TableView{
		Query: "SELECT * FROM table",
	}
	b7 := &Code{
		Contents: "SELECT * FROM table",
		Lang:     "sql",
	}
	b8 := &Link{
		Url:      "https://example.com",
		Contents: "Link 1",
	}

	mmm := ColorfulEcosystem{
		Title: "asdf",
		Things: []SyntaxNode{
			b1, b2, b3, b4, b5, b6, b7, b8,
		},
	}

	// Serialise to JSON
	jsonNote, err := json.Marshal(mmm)
	if err != nil {
		fmt.Println(err)
	}
	// fmt.Println(string(jsonNote))

	// Deserialise from JSON
	var mmm2 ColorfulEcosystem
	err = json.Unmarshal(jsonNote, &mmm2)
	if err != nil {
		fmt.Println(err)
	}

	// TODO: test

	// fmt.Println(mmm2.Title)
	// for _, thing := range mmm2.Things {
	// 	fmt.Println(thing.Md())
	// }
}
