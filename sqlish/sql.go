package sqlish

import (
	"fmt"
	"sort"
	"strconv"
	"strings"

	pml "github.com/hexylena/pm/log"
	"golang.org/x/exp/maps"
)

type SqlLikeQuery struct {
	Select  string
	From    string
	Where   string
	GroupBy string
	OrderBy string
	Limit   int
}

var logger = pml.L("models")

func (slq *SqlLikeQuery) String() string {
	return fmt.Sprintf("Select=[%s] From=[%s] Where=[%s] GroupBy=[%s] OrderBy=[%s] Limit=[%d]", slq.Select, slq.From, slq.Where, slq.GroupBy, slq.OrderBy, slq.Limit)
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
	Rows   map[string][][]string
}

func (slq *SqlLikeQuery) whereDocumentIsIncluded(document map[string]string, where string) bool {
	if where == "" {
		return true
	}

	if strings.Contains(where, "!=") {
		left := strings.TrimSpace(strings.Split(where, "!=")[0])
		right := strings.Split(where, "!=")[1]
		right = strings.Replace(right, "\"", "", -1)
		right = strings.Replace(right, "'", "", -1)
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
		right = strings.Replace(right, "\"", "", -1)
		right = strings.Replace(right, "'", "", -1)
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

	if slq.OrderBy != "" {
		// TODO parse multiple fields: Status ASC, created ASC
		field := strings.Split(slq.OrderBy, " ")[0]
		direction := strings.Split(slq.OrderBy, " ")[1]
		logger.Info("ORDER BY", "field", field, "direction", direction, "orig", slq.OrderBy)
		sort.Slice(documents, func(i, j int) bool {
			if direction == "ASC" {
				return documents[i][field] < documents[j][field]
			} else {
				return documents[i][field] > documents[j][field]
			}
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
		Rows:   map[string][][]string{},
	}

	if slq.GroupBy == "" {
		results.Rows["__default__"] = [][]string{}
		for _, document := range documents2 {
			row, header := Select(document, slq.Select)
			results.Rows["__default__"] = append(results.Rows["__default__"], row)
			if results.Header == nil {
				results.Header = header
			}
		}
	} else {
		// fmt.Printf("Grouping by: «%s»\n", slq.GroupBy)
		for _, document := range documents2 {
			// fmt.Printf("Grouping by: «%s»\n", document[slq.GroupBy])
			key := document[slq.GroupBy]
			if key == "" {
				key = "Uncategorized"
			}
			if _, ok := results.Rows[key]; !ok {
				results.Rows[key] = [][]string{}
			}
			row, header := Select(document, slq.Select)
			results.Rows[key] = append(results.Rows[key], row)

			if results.Header == nil {
				results.Header = header
			}
		}
	}

	// Limit: resize all groups to keep count under the limit num
	budget := slq.Limit
	if slq.Limit != -1 {
		for group, rows := range results.Rows {
			// if we've seen enough rows, truncate the rest
			if budget <= 0 {
				delete(results.Rows, group)
				continue
			} else {
				logger.Debug("Limiting Rows", "group", group, "rows", len(rows), "budget", budget, "limit", slq.Limit)
				// if we have too many rows for our budget
				if len(rows) > budget {
					results.Rows[group] = rows[:budget]
				}
			}
			budget -= len(rows)
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
