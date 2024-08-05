package models

import (
	"encoding/json"
	"fmt"
	"sort"

	pmd "github.com/hexylena/pm/md"
	"golang.org/x/exp/maps"
)

type Note0 struct {
	NoteId NoteId `yaml:"id" json:"id"`
	Title  string `json:"title"`
	Type   string `json:"type"`

	Projects []NoteId `json:"projects"`
	Parents  []NoteId `json:"parents"`
	Blocking []NoteId `json:"blocking"`

	Blocks     []pmd.SyntaxNode `json:"_blocks" yaml:"-"`
	Meta       []*Meta          `json:"_tags" yaml:"tags"`
	CreatedAt  int              `json:"created"`
	ModifiedAt int              `json:"modified"`
	modified   bool
}

func (ce *Note0) UnmarshalJSON(b []byte) error {
	// First, deserialize everything into a map of map
	var objMap map[string]*json.RawMessage
	err := json.Unmarshal(b, &objMap)
	if err != nil {
		return err
	}

	// Must manually deserialise each item
	if objMap["id"] != nil {
		err = json.Unmarshal(*objMap["id"], &ce.NoteId)
		if err != nil {
			return err
		}
	}

	if objMap["title"] != nil {
		err = json.Unmarshal(*objMap["title"], &ce.Title)
		if err != nil {
			return err
		}
	}

	if objMap["type"] != nil {
		err = json.Unmarshal(*objMap["type"], &ce.Type)
		if err != nil {
			return err
		}
	}

	if objMap["projects"] != nil {
		err = json.Unmarshal(*objMap["projects"], &ce.Projects)
		if err != nil {
			return err
		}
	}

	if objMap["parents"] != nil {
		err = json.Unmarshal(*objMap["parents"], &ce.Parents)
		if err != nil {
			return err
		}
	}

	if objMap["blocking"] != nil {
		err = json.Unmarshal(*objMap["blocking"], &ce.Blocking)
		if err != nil {
			return err
		}
	}

	if objMap["created"] != nil {
		err = json.Unmarshal(*objMap["created"], &ce.CreatedAt)
		if err != nil {
			return err
		}
	}

	if objMap["modified"] != nil {
		err = json.Unmarshal(*objMap["modified"], &ce.ModifiedAt)
		if err != nil {
			return err
		}
	}

	if objMap["_tags"] != nil {
		err = json.Unmarshal(*objMap["_tags"], &ce.Meta)
		if err != nil {
			return err
		}
	}

	if objMap["_blocks"] != nil {
		var rawMessagesBlocks []*json.RawMessage
		err = json.Unmarshal(*objMap["_blocks"], &rawMessagesBlocks)
		if err != nil {
			logger.Error("error unmarshalling _blocks", "error", err)
			return err
		}

		// Let's add a place to store our de-serialized Plant and Animal structs
		ce.Blocks = make([]pmd.SyntaxNode, len(rawMessagesBlocks))

		var m map[string]interface{}
		for index, rawMessage := range rawMessagesBlocks {
			err = json.Unmarshal(*rawMessage, &m)
			if err != nil {
				return err
			}

			// Depending on the type, we can run json.Unmarshal again on the same byte slice
			// But this time, we'll pass in the appropriate struct instead of a map
			if m["type"] == "heading" {
				var p pmd.Heading
				err := json.Unmarshal(*rawMessage, &p)
				if err != nil {
					return err
				}
				// After creating our struct, we should save it
				ce.Blocks[index] = &p
			} else if m["type"] == "paragraph" {
				var a pmd.Paragraph
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				// After creating our struct, we should save it
				ce.Blocks[index] = &a
			} else if m["type"] == "image" {
				var a pmd.Image
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "list" {
				var a pmd.List
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "horizontal_rule" {
				var a pmd.HorizontalRule
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "table_view" {
				var a pmd.TableView
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "code" {
				var a pmd.Code
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "link" {
				var a pmd.Link
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else {
				return fmt.Errorf("Unknown type: %s", m["type"])
			}
		}
	}

	// That's it!  We made it the whole way with no errors, so we can return `nil`
	return nil
}

type Note1 struct {
	NoteId NoteId `yaml:"id" json:"id"`
	Title  string `json:"title"`
	Type   string `json:"type"`

	Projects []NoteId `json:"projects"`
	Parents  []NoteId `json:"parents"`
	Blocking []NoteId `json:"blocking"`

	Blocks     []pmd.SyntaxNode `json:"_blocks" yaml:"-"`
	Meta       []*Meta          `json:"_tags" yaml:"tags"`
	CreatedAt  int              `json:"created"`
	ModifiedAt int              `json:"modified"`
	modified   bool
	Version    int `json:"version"`
}

func (ce *Note1) UnmarshalJSON(b []byte) error {
	// First, deserialize everything into a map of map
	var objMap map[string]*json.RawMessage
	err := json.Unmarshal(b, &objMap)
	if err != nil {
		return err
	}

	// Must manually deserialise each item
	if objMap["id"] != nil {
		err = json.Unmarshal(*objMap["id"], &ce.NoteId)
		if err != nil {
			return err
		}
	}

	if objMap["title"] != nil {
		err = json.Unmarshal(*objMap["title"], &ce.Title)
		if err != nil {
			return err
		}
	}

	if objMap["version"] != nil {
		err = json.Unmarshal(*objMap["version"], &ce.Version)
		if err != nil {
			return err
		}
	}

	if objMap["type"] != nil {
		err = json.Unmarshal(*objMap["type"], &ce.Type)
		if err != nil {
			return err
		}
	}

	if objMap["projects"] != nil {
		err = json.Unmarshal(*objMap["projects"], &ce.Projects)
		if err != nil {
			return err
		}
	}

	if objMap["parents"] != nil {
		err = json.Unmarshal(*objMap["parents"], &ce.Parents)
		if err != nil {
			return err
		}
	}

	if objMap["blocking"] != nil {
		err = json.Unmarshal(*objMap["blocking"], &ce.Blocking)
		if err != nil {
			return err
		}
	}

	if objMap["created"] != nil {
		err = json.Unmarshal(*objMap["created"], &ce.CreatedAt)
		if err != nil {
			return err
		}
	}

	if objMap["modified"] != nil {
		err = json.Unmarshal(*objMap["modified"], &ce.ModifiedAt)
		if err != nil {
			return err
		}
	}

	if objMap["_tags"] != nil {
		err = json.Unmarshal(*objMap["_tags"], &ce.Meta)
		if err != nil {
			return err
		}
	}

	if objMap["_blocks"] != nil {
		var rawMessagesBlocks []*json.RawMessage
		err = json.Unmarshal(*objMap["_blocks"], &rawMessagesBlocks)
		if err != nil {
			logger.Error("error unmarshalling _blocks", "error", err)
			return err
		}

		// Let's add a place to store our de-serialized Plant and Animal structs
		ce.Blocks = make([]pmd.SyntaxNode, len(rawMessagesBlocks))

		var m map[string]interface{}
		for index, rawMessage := range rawMessagesBlocks {
			err = json.Unmarshal(*rawMessage, &m)
			if err != nil {
				return err
			}

			// Depending on the type, we can run json.Unmarshal again on the same byte slice
			// But this time, we'll pass in the appropriate struct instead of a map
			if m["type"] == "heading" {
				var p pmd.Heading
				err := json.Unmarshal(*rawMessage, &p)
				if err != nil {
					return err
				}
				// After creating our struct, we should save it
				ce.Blocks[index] = &p
			} else if m["type"] == "paragraph" {
				var a pmd.Paragraph
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				// After creating our struct, we should save it
				ce.Blocks[index] = &a
			} else if m["type"] == "image" {
				var a pmd.Image
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "list" {
				var a pmd.List
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "horizontal_rule" {
				var a pmd.HorizontalRule
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "table_view" {
				var a pmd.TableView
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "code" {
				var a pmd.Code
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "link" {
				var a pmd.Link
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else {
				return fmt.Errorf("Unknown type: %s", m["type"])
			}
		}
	}

	// That's it!  We made it the whole way with no errors, so we can return `nil`
	return nil
}

type Note2 struct {
	NoteId NoteId `yaml:"id" json:"id"`
	Title  string `json:"title"`
	Type   string `json:"type"`

	Parents  []NoteId `json:"parents"`
	Blocking []NoteId `json:"blocking"`

	Blocks     []pmd.SyntaxNode `json:"_blocks" yaml:"-"`
	Meta       []*Meta          `json:"_tags" yaml:"tags"`
	CreatedAt  int              `json:"created"`
	ModifiedAt int              `json:"modified"`
	modified   bool
	Version    int `json:"version"`
}

func (ce *Note2) UnmarshalJSON(b []byte) error {
	// First, deserialize everything into a map of map
	var objMap map[string]*json.RawMessage
	err := json.Unmarshal(b, &objMap)
	if err != nil {
		return err
	}

	// Must manually deserialise each item
	if objMap["id"] != nil {
		err = json.Unmarshal(*objMap["id"], &ce.NoteId)
		if err != nil {
			return err
		}
	}

	if objMap["title"] != nil {
		err = json.Unmarshal(*objMap["title"], &ce.Title)
		if err != nil {
			return err
		}
	}

	if objMap["version"] != nil {
		err = json.Unmarshal(*objMap["version"], &ce.Version)
		if err != nil {
			return err
		}
	}

	if objMap["type"] != nil {
		err = json.Unmarshal(*objMap["type"], &ce.Type)
		if err != nil {
			return err
		}
	}

	if objMap["parents"] != nil {
		err = json.Unmarshal(*objMap["parents"], &ce.Parents)
		if err != nil {
			return err
		}
	}

	if objMap["blocking"] != nil {
		err = json.Unmarshal(*objMap["blocking"], &ce.Blocking)
		if err != nil {
			return err
		}
	}

	if objMap["created"] != nil {
		err = json.Unmarshal(*objMap["created"], &ce.CreatedAt)
		if err != nil {
			return err
		}
	}

	if objMap["modified"] != nil {
		err = json.Unmarshal(*objMap["modified"], &ce.ModifiedAt)
		if err != nil {
			return err
		}
	}

	if objMap["_tags"] != nil {
		err = json.Unmarshal(*objMap["_tags"], &ce.Meta)
		if err != nil {
			return err
		}
	}

	if objMap["_blocks"] != nil {
		var rawMessagesBlocks []*json.RawMessage
		err = json.Unmarshal(*objMap["_blocks"], &rawMessagesBlocks)
		if err != nil {
			logger.Error("error unmarshalling _blocks", "error", err)
			return err
		}

		// Let's add a place to store our de-serialized Plant and Animal structs
		ce.Blocks = make([]pmd.SyntaxNode, len(rawMessagesBlocks))

		var m map[string]interface{}
		for index, rawMessage := range rawMessagesBlocks {
			err = json.Unmarshal(*rawMessage, &m)
			if err != nil {
				return err
			}

			// Depending on the type, we can run json.Unmarshal again on the same byte slice
			// But this time, we'll pass in the appropriate struct instead of a map
			if m["type"] == "heading" {
				var p pmd.Heading
				err := json.Unmarshal(*rawMessage, &p)
				if err != nil {
					return err
				}
				// After creating our struct, we should save it
				ce.Blocks[index] = &p
			} else if m["type"] == "paragraph" {
				var a pmd.Paragraph
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				// After creating our struct, we should save it
				ce.Blocks[index] = &a
			} else if m["type"] == "image" {
				var a pmd.Image
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "list" {
				var a pmd.List
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "horizontal_rule" {
				var a pmd.HorizontalRule
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "table_view" {
				var a pmd.TableView
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "code" {
				var a pmd.Code
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "link" {
				var a pmd.Link
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else {
				return fmt.Errorf("Unknown type: %s", m["type"])
			}
		}
	}

	// That's it!  We made it the whole way with no errors, so we can return `nil`
	return nil
}

// Migrate returns the latest note version
func Migrate(bytes []byte, n *Note) {
	version := GetVersion(bytes)
	logger.Debug("Parsed Version", "version", version)

	var n0 Note0
	var n1 Note1
	var n2 Note2

	if version == 0 {
		err := json.Unmarshal(bytes, &n0)
		if err != nil {
			logger.Error("Error unmarshaling v0", "error", err)
		}
	} else if version == 1 {
		err := json.Unmarshal(bytes, &n1)
		if err != nil {
			logger.Error("Error unmarshaling v1", "error", err)
		}
	} else if version == 2 {
		err := json.Unmarshal(bytes, &n2)
		if err != nil {
			logger.Error("Error unmarshaling v2", "error", err)
		}
	}
	logger.Debug("Parsed Version", "version", version, "n0", n0.NoteId, "n1", n1.NoteId, "n2", n2.NoteId)

	if version == 0 {
		n1 = migrate1(n0)
		version = 1
	}

	logger.Debug("Parsed Version", "version", version, "n0", n0.NoteId, "n1", n1.NoteId, "n2", n2.NoteId)

	if version == 1 {
		n2 = migrate2(n1)
		version = 2
	}
	logger.Debug("Parsed Version", "version", version, "n0", n0.NoteId, "n1", n1.NoteId, "n2", n2.NoteId)

	// LATEST version is compatible with Note (no number)
	n_bytes, err := json.Marshal(n2)
	if err != nil {
		logger.Error("Error marshaling", "error", err)
	}
	logger.Debug("Marshaled", "note", n_bytes)

	err = json.Unmarshal(n_bytes, n)
	if err != nil {
		logger.Error("Error unmarshaling", "error", err)
	}
	logger.Debug("Finalised", "note", n)
}

func migrate1(n0 Note0) Note1 {
	n1 := Note1{
		NoteId:     n0.NoteId,
		Title:      n0.Title,
		Type:       n0.Type,
		Projects:   n0.Projects,
		Parents:    n0.Parents,
		Blocking:   n0.Blocking,
		Blocks:     n0.Blocks,
		Meta:       n0.Meta,
		CreatedAt:  n0.CreatedAt,
		ModifiedAt: n0.ModifiedAt,
		modified:   n0.modified,
		Version:    1,
	}

	return n1
}

func migrate2(n1 Note1) Note2 {
	// n1.projects and n1.parents need to be merged + unique'd
	parents_map := make(map[NoteId]bool)
	for _, p := range append(n1.Parents, n1.Projects...) {
		parents_map[p] = true
	}

	parents := maps.Keys(parents_map)

	sort.Slice(parents, func(i, j int) bool {
		a := string(parents[i])
		b := string(parents[j])
		return a < b
	})

	n2 := Note2{
		NoteId: n1.NoteId,
		Title:  n1.Title,
		Type:   n1.Type,
		// Projects: n1.Projects,
		// append projects to parents
		// Unique values
		Parents:    parents,
		Blocking:   n1.Blocking,
		Blocks:     n1.Blocks,
		Meta:       n1.Meta,
		CreatedAt:  n1.CreatedAt,
		ModifiedAt: n1.ModifiedAt,
		modified:   n1.modified,
		Version:    2,
	}

	return n2
}

func GetVersion(bytes []byte) int {
	var objmap map[string]interface{}
	err := json.Unmarshal(bytes, &objmap)
	if err != nil {
		fmt.Println(err)
	}

	// if there is no version key
	// then it is version 0
	if _, ok := objmap["version"]; !ok {
		return 0
	}
	// parse version as int
	return int(objmap["version"].(float64))
}
