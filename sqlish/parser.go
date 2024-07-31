package sqlish

import (
	"fmt"
	"github.com/blastrain/vitess-sqlparser/sqlparser"
	"strconv"
	"strings"
	// "reflect"
)

func processComparison(s *sqlparser.ComparisonExpr) string {
	left := colname_or_value(s.Left)
	right := colname_or_value(s.Right)
	comparison := s.Operator
	where := fmt.Sprintf("%s %s %s", left, comparison, string(right))
	return where
}

func colname_or_value(w sqlparser.Expr) string {
	if col, _ := w.(*sqlparser.ColName); col != nil {
		return col.Name.CompliantName()
	} else if col, _ := w.(*sqlparser.SQLVal); col != nil {
		return string(col.Val)
	} else {
		panic("Unknown type")
	}
}

func parseQuery(query string) *SqlLikeQuery {
	// stmt, err := sqlparser.Parse("select id, name, Random from asdf where user_id=1 group by project, 'by' order by created_at DESC, create_time asc limit 3 offset 10")
	// stmt, err := sqlparser.Parse("select id, name, Random from asdf")
	// stmt, err := sqlparser.Parse("select id, name, Random from asdf where user_id=1 order by created_at limit 3 offset 10")
	// stmt, err := sqlparser.Parse("select id, name, Random from asdf where user_id = 1234567890 ")
	// stmt, err := sqlparser.Parse("select id, name, Random from asdf where project_id != '2a' ")
	// stmt, err := sqlparser.Parse("select id, name, Random from asdf where user_id = 1234567890 and project_id != '2a' ")
	// stmt, err := sqlparser.Parse("select id, name, Random from asdf group by project_id, name")
	stmt, err := sqlparser.Parse(query)
	if err != nil {
		fmt.Printf("Error parsing query: %s\n", query)
		panic(err)
	}
	// fmt.Printf("stmt = %+v\n", stmt)

	selectStmt := stmt.(*sqlparser.Select)
	if selectStmt == nil {
		panic("Not a select statement")
	}

	// select
	res_select := []string{}
	if selects := selectStmt.SelectExprs; selects != nil {
		for _, w := range selects {
			if _, ok := w.(*sqlparser.StarExpr); ok {
				res_select = append(res_select, "*")
			} else {
				term := fmt.Sprintf("%s", w.(*sqlparser.AliasedExpr).Expr.(*sqlparser.ColName).Name)
				res_select = append(res_select, term)
			}
		}
	}
	// from
	from := fmt.Sprintf("%s", selectStmt.From[0].(*sqlparser.AliasedTableExpr).Expr.(sqlparser.TableName).Name)

	// where
	where := ""
	if selectStmt.Where != nil {
		// if it's an ComparisonExpr
		// fmt.Printf("%s\n", selectStmt.Where)
		if s, _ := selectStmt.Where.Expr.(*sqlparser.ComparisonExpr); s != nil {
			where = processComparison(s)
		}

		if s, _ := selectStmt.Where.Expr.(*sqlparser.AndExpr); s != nil {
			where_1 := processComparison(s.Left.(*sqlparser.ComparisonExpr))
			where_2 := processComparison(s.Right.(*sqlparser.ComparisonExpr))
			where = fmt.Sprintf("%s AND %s", where_1, where_2)
		}

		if s, _ := selectStmt.Where.Expr.(*sqlparser.OrExpr); s != nil {
			where_1 := processComparison(s.Left.(*sqlparser.ComparisonExpr))
			where_2 := processComparison(s.Right.(*sqlparser.ComparisonExpr))
			where = fmt.Sprintf("%s OR %s", where_1, where_2)
		}

		// ZERO support for more complex queries.
	}

	// group by
	groupBy := ""
	// fmt.Printf("%s\n", selectStmt.GroupBy)
	if s := selectStmt.GroupBy; s != nil {
		res_group := []string{}
		for _, w := range s {
			term := ""
			term = colname_or_value(w)
			res_group = append(res_group, term)
		}
		groupBy = strings.Join(res_group, ", ")
	}

	// order by
	orderBy := ""
	if s := selectStmt.OrderBy; s != nil {
		res_order := []string{}
		for _, w := range s {
			term := ""
			// type of w
			term = colname_or_value(w.Expr)
			direction := strings.ToUpper(w.Direction)
			res_order = append(res_order, fmt.Sprintf("%s %s", term, direction))
		}
		orderBy = strings.Join(res_order, ", ")
	}

	// limit
	limit := -1
	if s := selectStmt.Limit; s != nil {
		if s.Rowcount != nil {

			limit_s := string(s.Rowcount.(*sqlparser.SQLVal).Val)
			fmt.Printf("LIMIT %s\n", limit_s)

			// parse string to int
			limit, err = strconv.Atoi(limit_s)
			if err != nil {
				panic(err)
			}
		}
	}

	q := &SqlLikeQuery{
		Select:  strings.Join(res_select, ", "),
		From:    from,
		Where:   where,
		GroupBy: groupBy,
		OrderBy: orderBy,
		Limit:   limit,
	}
	fmt.Println(q)
	return q
}
