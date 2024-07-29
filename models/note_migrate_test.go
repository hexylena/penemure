package models_test

import (
	pmm "github.com/hexylena/pm/models"
	"testing"
)

const minimal_v0 = `
{
  "id": "23ab5629-1e89-49b6-b05d-ccf6b36b264c",
  "title": "asdf",
  "type": "project",
  "projects": [
    "00000000-0000-0000-0000-222222222222",
    "00000000-0000-0000-0000-333333333333"
  ],
  "parents": [
    "00000000-0000-0000-0000-000000000000",
    "00000000-0000-0000-0000-111111111111"
  ],
  "blocking": [],
  "_blocks": null,
  "_tags": [],
  "created": 1700000000,
  "modified": 1700001111
}
`

const minimal_v1 = `
{
  "id": "23ab5629-1e89-49b6-b05d-ccf6b36b264c",
  "title": "",
  "type": "",
  "projects": [
    "00000000-0000-0000-0000-222222222222",
    "00000000-0000-0000-0000-333333333333"
  ],
  "parents": [
    "00000000-0000-0000-0000-000000000000",
    "00000000-0000-0000-0000-111111111111"
  ],
  "blocking": [],
  "_blocks": null,
  "_tags": [],
  "created": 1706176264,
  "modified": 1706176267,
  "version": 1
}
`

func TestVersion(t *testing.T) {
	v0 := pmm.GetVersion([]byte(minimal_v0))
	if v0 != 0 {
		t.Errorf("o:«%d» != e:«%d»", v0, 0)
	}

	v1 := pmm.GetVersion([]byte(minimal_v1))
	if v1 != 1 {
		t.Errorf("o:«%d» != e:«%d»", v1, 1)
	}
}

func TestMigrateToLatest(t *testing.T) {
	v0v := pmm.GetVersion([]byte(minimal_v0))
	if v0v != 0 {
		t.Errorf("o:«%d» != e:«%d»", v0v, 0)
	}

	v0 := pmm.Migrate([]byte(minimal_v0))
	if v0.Version != 2 {
		t.Errorf("o:«%d» != e:«%d»", v0.Version, 2)
	}
}

func TestMigrateParents(t *testing.T) {
	v0 := pmm.Migrate([]byte(minimal_v0))

	if len(v0.Parents) != 4 {
		t.Errorf("o:«%d» != e:«%d»", v0.Version, 2)
	}
	// check parents
	expected_parents := []pmm.NoteId{
		"00000000-0000-0000-0000-000000000000",
		"00000000-0000-0000-0000-111111111111",
		"00000000-0000-0000-0000-222222222222",
		"00000000-0000-0000-0000-333333333333",
	}
	for i, parent := range v0.Parents {
		if expected_parents[i] != parent {
			t.Errorf("o:«%s» != e:«%s»", parent, expected_parents[i])
		}
	}
}
