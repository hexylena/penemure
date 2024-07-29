package models

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	pmd "github.com/hexylena/pm/md"
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
	Version int `json:"version"`
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
	Version int `json:"version"`
}

func loadJson(path string) []byte {
	jsonFile, err := os.Open(path)
	if err != nil {
		fmt.Println(err)
	}
	defer jsonFile.Close()

	byteValue, err := ioutil.ReadAll(jsonFile)
	if err != nil {
		fmt.Println(err)
	}

	return byteValue
}

// Returns the latest note version
func Migrate(bytes []byte) Note2 {
	version := GetVersion(bytes)

	var n0 Note0
	var n1 Note1
	var n2 Note2

	if version == 0 {
		err := json.Unmarshal(bytes, &n0)
		if err != nil {
			fmt.Println(err)
		}
	} else if version == 1 {
		err := json.Unmarshal(bytes, &n1)
		if err != nil {
			fmt.Println(err)
		}
	} else if version == 2 {
		err := json.Unmarshal(bytes, &n2)
		if err != nil {
			fmt.Println(err)
		}
	}
	
	if version == 0 {
		n1 = migrate1(n0)
		version = 1
	}

	if version == 1 {
		n2 = migrate2(n1)
		version = 2
	}

	return n2
}

func migrate1(n0 Note0) Note1 {
	n1 := Note1{
		NoteId: n0.NoteId,
		Title: n0.Title,
		Type: n0.Type,
		Projects: n0.Projects,
		Parents: n0.Parents,
		Blocking: n0.Blocking,
		Blocks: n0.Blocks,
		Meta: n0.Meta,
		CreatedAt: n0.CreatedAt,
		ModifiedAt: n0.ModifiedAt,
		modified: n0.modified,
		Version: 1,
	}

	return n1
}

func migrate2(n1 Note1) Note2 {
	n2 := Note2{
		NoteId: n1.NoteId,
		Title: n1.Title,
		Type: n1.Type,
		// Projects: n1.Projects,
		// append projects to parents
		Parents: append(n1.Parents, n1.Projects...),
		Blocking: n1.Blocking,
		Blocks: n1.Blocks,
		Meta: n1.Meta,
		CreatedAt: n1.CreatedAt,
		ModifiedAt: n1.ModifiedAt,
		modified: n1.modified,
		Version: 2,
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
	// return int(objmap["version"].(float64))
	return 1
}

