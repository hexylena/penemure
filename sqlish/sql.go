package sqlish

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

type SqlLikeQuery struct {
	Select  string
	From    string
	Where   string
	GroupBy string
	OrderBy string
	Limit   int
}

func (slq *SqlLikeQuery) String() string {
	return fmt.Sprintf("Select=[%s] Table=[%s] Where=[%s] GroupBy=[%s] OrderBy=[%s] Limit=[%d]", slq.Select, slq.From, slq.Where, slq.GroupBy, slq.OrderBy, slq.Limit)
}

func ParseSelectFrom(query string) *SqlLikeQuery {
	sqlLike := regexp.MustCompile(`^SELECT\s+([a-z*, ]+)\s+FROM\s+([a-z]+)$`) //
	m := sqlLike.FindStringSubmatch(query)

	slq := &SqlLikeQuery{
		Select: m[1],
		From:   m[2],
	}
	return slq
}

func ParseSqlQuery(query string) *SqlLikeQuery {
	sqlLike := regexp.MustCompile(`^SELECT\s+([a-z_, ]+)\s+FROM\s+([a-z]+)(\s+WHERE ([a-z<>=!0-9'" -]+))?( GROUP BY ([A-Za-z]+))?(\s+ORDER BY ([a-z]+) (ASC|DESC))?(\s+LIMIT ([0-9]+))?$`) //

	m := sqlLike.FindStringSubmatch(query)
	if len(m) < 9 {
		fmt.Println("Error parsing query: ", query)
		return &SqlLikeQuery{}
	}

	limit, err := strconv.Atoi(m[11])
	if err != nil {
		limit = -1
	}

	slq := &SqlLikeQuery{
		Select:  strings.TrimSpace(m[1]),
		From:    strings.TrimSpace(m[2]),
		Where:   strings.TrimSpace(m[4]),
		GroupBy: strings.TrimSpace(m[6]),
		OrderBy: strings.TrimSpace(m[8] + " " + m[9]),
		Limit:   limit,
	}
	return slq
}

func (slq *SqlLikeQuery) GetFields() []string {
	r := []string{}
	for _, field := range strings.Split(slq.Select, ",") {
		r = append(r, strings.TrimSpace(field))
	}
	return r
}

type GroupedResultSet map[string][][]string

func (slq *SqlLikeQuery) FilterDocuments(documents []map[string]string) GroupedResultSet {
	// fmt.Println("Filtering documents with query: ", slq)
	// OrderBy
	if slq.OrderBy != "" {
		field := strings.Split(slq.OrderBy, " ")[0]
		direction := strings.Split(slq.OrderBy, " ")[1]
		sort.Slice(documents, func(i, j int) bool {
			if direction == "ASC" {
				return documents[i][field] < documents[j][field]
			} else {
				return documents[i][field] > documents[j][field]
			}
		})
	}

	documents2 := []map[string]string{}
	// Where
	if slq.Where != "" {
		for _, document := range documents {
			// Currently only support 'simple' filters, id=1 or project != "asdf"
			if strings.Contains(slq.Where, "!=") {
				left := strings.TrimSpace(strings.Split(slq.Where, "!=")[0])
				right := strings.Split(slq.Where, "!=")[1]
				right = strings.Replace(right, "\"", "", -1)
				right = strings.Replace(right, "'", "", -1)
				right = strings.TrimSpace(right)

				if document[left] != right {
					documents2 = append(documents2, document)
				}
			} else if strings.Contains(slq.Where, ">=") {
				panic("Not implemented: >=")
			} else if strings.Contains(slq.Where, "<=") {
				panic("Not implemented: <=")
			} else if strings.Contains(slq.Where, "=") {
				left := strings.TrimSpace(strings.Split(slq.Where, "=")[0])
				right := strings.Split(slq.Where, "=")[1]
				right = strings.Replace(right, "\"", "", -1)
				right = strings.Replace(right, "'", "", -1)
				right = strings.TrimSpace(right)
				// fmt.Printf("Halves: «%s» «%s»", left, right)
				// fmt.Println("Comparing: ", document[left], right)

				// projects, parents, and blocking are special, they're strings joined by a separator character so we need to check contains
				if left == "project" || left == "parent" || left == "blocking" {
					if strings.Contains(document[left], right) {
						documents2 = append(documents2, document)
					}
				} else if document[left] == right {
					documents2 = append(documents2, document)
				}
			}
		}
	}

	// From (table)
	// I think we should ignore this??? maybe?? Or maybe it should be based
	// on the git repo someday?

	// group by + select
	results := make(GroupedResultSet, 0)
	if slq.GroupBy == "" {
		results["__default__"] = [][]string{}
		for _, document := range documents2 {
			results["__default__"] = append(results["__default__"], Select(document, slq.Select))
		}
	} else {
		fmt.Printf("Grouping by: «%s»\n", slq.GroupBy)
		for _, document := range documents2 {
			fmt.Printf("Grouping by: «%s»\n", document[slq.GroupBy])
			key := document[slq.GroupBy]
			if key == "" {
				key = "Uncategorized"
			}
			if _, ok := results[key]; !ok {
				results[key] = [][]string{}
			}
			results[key] = append(results[key], Select(document, slq.Select))
		}
	}

	// Limit: last
	if slq.Limit > 0 {
		panic("Not implemented: limit")
	}
	return results
}

func Select(document map[string]string, fields string) []string {
	r := []string{}
	for _, field := range strings.Split(fields, ",") {
		r = append(r, document[strings.TrimSpace(field)])
	}
	return r
}
