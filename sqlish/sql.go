package sqlish

import (
	"fmt"
	"sort"
	"strconv"
	"strings"

	pml "github.com/hexylena/pm/log"
	"golang.org/x/exp/maps"
)

type SqlSorting struct {
	Field string
	ASC   bool
}

func (s *SqlSorting) String() string {
	if s.ASC {
		return fmt.Sprintf("%s ASC", s.Field)
	}
	return fmt.Sprintf("%s DESC", s.Field)
}

type SqlLikeQuery struct {
	Select  string
	From    string
	Where   string
	GroupBy string
	OrderBy []SqlSorting
	Limit   int
}

var logger = pml.L("models")

func (slq *SqlLikeQuery) String() string {
	return fmt.Sprintf("Select=[%s] From=[%s] Where=[%s] GroupBy=[%s] OrderBy=[%v] Limit=[%d]",
		slq.Select, slq.From, slq.Where, slq.GroupBy, slq.OrderBy, slq.Limit)
}

func ParseSqlQuery(query string) *SqlLikeQuery {
	return parseQuery(query)
}

func (slq *SqlLikeQuery) GetFields() []string {
	r := []string{}

	// if slq.Select == "*" {
	// 	for _, field := range maps.Keys() {
	// 		r = append(r, field)
	// 	}
	// } else {
	for _, field := range strings.Split(slq.Select, ",") {
		r = append(r, strings.TrimSpace(field))
	}
	// }
	return r
}

type GroupedResultSet struct {
	Header []string
	Rows   []ResultSet
}

type ResultSet struct {
	Title string
	Data  [][]string
}

func (slq *SqlLikeQuery) whereDocumentIsIncluded(document map[string]string, where string) bool {
	if where == "" {
		return true
	}

	if strings.Contains(where, "!=") {
		left := strings.TrimSpace(strings.Split(where, "!=")[0])
		right := strings.Split(where, "!=")[1]
		right = strings.ReplaceAll(right, "\"", "")
		right = strings.ReplaceAll(right, "'", "")
		right = strings.TrimSpace(right)

		if document[left] != right {
			return true
		}
	} else if strings.Contains(where, ">=") {
		panic("Not implemented: >=")
	} else if strings.Contains(where, "<=") {
		panic("Not implemented: <=")
	} else if strings.Contains(where, "=") {
		left := strings.TrimSpace(strings.Split(where, "=")[0])
		right := strings.Split(where, "=")[1]
		right = strings.ReplaceAll(right, "\"", "")
		right = strings.ReplaceAll(right, "'", "")
		right = strings.TrimSpace(right)
		// fmt.Printf("Halves: «%s» «%s»", left, right)
		// fmt.Println("Comparing: ", document[left], right)

		// projects, parents, and blocking are special, they're strings joined by a separator character so we need to check contains
		logger.Debug("where=", "left", left, "right", right, "doc left", document[left])
		if left == "project" || left == "parent" || left == "blocking" {
			if strings.Contains(document[left], right) {
				return true
			}
		} else if document[left] == right {
			return true
			// documents2 = append(documents2, document)
		}
	} else if strings.Contains(where, "is null") {
		left := strings.TrimSpace(strings.Split(where, "is null")[0])
		if document[left] == "" {
			return true
		}
	} else if strings.Contains(where, "is not null") {
		panic("Not implemented: is not null")
	}
	return false
}

func (slq *SqlLikeQuery) FilterDocuments(documents []map[string]string) *GroupedResultSet {
	// fmt.Println("Filtering documents with query: ", slq)
	// OrderBy
	logger.Debug("Filtering documents with query", "query", slq)
	logger.Debug("Initial Documents", "count", len(documents))

	if slq.OrderBy != nil {
		// TODO parse multiple fields: Status ASC, created ASC
		// sorters := strings.Split(slq.OrderBy, ", ")

		logger.Info("ORDER BY", "orig", slq.OrderBy)
		sort.Slice(documents, func(i, j int) bool {
			for _, s := range slq.OrderBy {
				if s.ASC {
					if documents[i][s.Field] == documents[j][s.Field] {
						continue
					}
					return documents[i][s.Field] < documents[j][s.Field]
				} else {
					if documents[i][s.Field] == documents[j][s.Field] {
						continue
					}
					return documents[i][s.Field] > documents[j][s.Field]
				}
			}
			return false
		})
	}

	logger.Debug("Post Order Documents", "count", len(documents))

	documents2 := []map[string]string{}

	// Where
	for _, document := range documents {
		logger.Debug("Filtering Documents", "where", slq.Where, "doc", document)
		if strings.Contains(slq.Where, " AND ") {
			terms := strings.Split(slq.Where, " AND ")
			if slq.whereDocumentIsIncluded(document, terms[0]) && slq.whereDocumentIsIncluded(document, terms[1]) {
				documents2 = append(documents2, document)
			}

		} else if strings.Contains(slq.Where, " OR ") {
			terms := strings.Split(slq.Where, " OR ")
			if slq.whereDocumentIsIncluded(document, terms[0]) || slq.whereDocumentIsIncluded(document, terms[1]) {
				documents2 = append(documents2, document)
			}
		} else {
			if slq.whereDocumentIsIncluded(document, slq.Where) {
				documents2 = append(documents2, document)
			}
		}
	}

	logger.Debug("Post Where Documents", "count", len(documents2))

	// From (table)
	// I think we should ignore this??? maybe?? Or maybe it should be based
	// on the git repo someday?

	// group by + select
	results := &GroupedResultSet{
		Header: nil,
		Rows:   make([]ResultSet, 0),
	}
	rs_index := make(map[string]int, 0)

	// Limit occurs simultaneoulsy for efficiency
	budget := slq.Limit
	// If the budget ever hits 0 exactly processing stops (it isn't batched, and <=-1 is an indicator for "process all please")

	if slq.GroupBy == "" {
		rs := ResultSet{Title: "__default__", Data: make([][]string, 0)}
		for _, document := range documents2 {
			row, header := Select(document, slq.Select)

			if results.Header == nil {
				results.Header = header
			}

			if budget > 0 || budget <= -1 {
				rs.Data = append(rs.Data, row)
				budget -= 1
			}
		}
		results.Rows = append(results.Rows, rs)
	} else {
		// fmt.Printf("Grouping by: «%s»\n", slq.GroupBy)
		for _, document := range documents2 {
			logger.Debug("Doc", "budget", budget)
			// fmt.Printf("Grouping by: «%s»\n", document[slq.GroupBy])
			key := document[slq.GroupBy]
			if key == "" {
				key = "Uncategorized"
			}

			if _, ok := rs_index[key]; !ok {
				rs := ResultSet{Title: key, Data: make([][]string, 0)}
				results.Rows = append(results.Rows, rs)
				rs_index[key] = len(results.Rows) - 1
			}

			row, header := Select(document, slq.Select)
			index := rs_index[key]

			if budget > 0 || budget <= -1 {

				results.Rows[index].Data = append(results.Rows[index].Data, row)
				budget -= 1
			}

			if results.Header == nil {
				results.Header = header
			}
		}
	}

	return results
}

func Select(document map[string]string, fields string) ([]string, []string) {
	row := []string{}
	header := []string{}

	if fields == "*" {
		for _, field := range maps.Keys(document) {
			row = append(row, document[field])
			header = append(header, field)
		}

	} else {
		for _, field := range strings.Split(fields, ",") {
			if strings.Contains(field, " - ") {
				left := strings.TrimSpace(strings.Split(field, " - ")[0])
				right := strings.TrimSpace(strings.Split(field, " - ")[1])
				if document[left] == "" || document[right] == "" {
					row = append(row, "NaN")
					header = append(header, strings.TrimSpace(field))
					continue
				}
				left_f, _ := strconv.ParseFloat(document[left], 64)
				right_f, _ := strconv.ParseFloat(document[right], 64)
				res := left_f - right_f
				// if res is an integer
				if res == float64(int(res)) {
					row = append(row, fmt.Sprintf("%d", int(res)))
				} else {
					row = append(row, fmt.Sprintf("%f", res))
				}
				header = append(header, strings.TrimSpace(field))
			} else {
				row = append(row, document[strings.TrimSpace(field)])
				header = append(header, strings.TrimSpace(field))
			}
		}
	}
	return row, header
}
