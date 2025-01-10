package sqlish

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/blastrain/vitess-sqlparser/sqlparser"
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
			} else if expr, ok := w.(*sqlparser.AliasedExpr).Expr.(*sqlparser.BinaryExpr); ok {
				op := string(expr.Operator)
				left := colname_or_value(expr.Left)
				right := colname_or_value(expr.Right)
				res_select = append(res_select, fmt.Sprintf("%s %s %s", left, op, right))
			} else {
				term := string(colname_or_value(w.(*sqlparser.AliasedExpr).Expr))
				res_select = append(res_select, term)
			}
		}
	}
	// from
	from := selectStmt.From[0].(*sqlparser.AliasedTableExpr).Expr.(sqlparser.TableName).Name.String()

	// where
	where := ""
	if selectStmt.Where != nil {
		// if it's an ComparisonExpr
		if s, _ := selectStmt.Where.Expr.(*sqlparser.ComparisonExpr); s != nil {
			where = processComparison(s)
		} else if s, _ := selectStmt.Where.Expr.(*sqlparser.AndExpr); s != nil {
			where_1 := processComparison(s.Left.(*sqlparser.ComparisonExpr))
			where_2 := processComparison(s.Right.(*sqlparser.ComparisonExpr))
			where = fmt.Sprintf("%s AND %s", where_1, where_2)
		} else if s, _ := selectStmt.Where.Expr.(*sqlparser.OrExpr); s != nil {
			where_1 := processComparison(s.Left.(*sqlparser.ComparisonExpr))
			where_2 := processComparison(s.Right.(*sqlparser.ComparisonExpr))
			where = fmt.Sprintf("%s OR %s", where_1, where_2)
		} else if s, _ := selectStmt.Where.Expr.(*sqlparser.IsExpr); s != nil {
			// where = s.Operator
			where = fmt.Sprintf("%s %s", colname_or_value(s.Expr), s.Operator)
		} else {
			fmt.Printf("Unknown type: %T\n", selectStmt.Where.Expr)
			panic("Unknown type")
		}

		// ZERO support for more complex queries.
	} else {
		fmt.Println("No where clause")
	}

	// group by
	groupBy := ""
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
	orderBy := make([]SqlSorting, 0)
	if s := selectStmt.OrderBy; s != nil {
		for _, w := range s {
			term := ""
			// type of w
			term = colname_or_value(w.Expr)
			direction := strings.ToUpper(w.Direction)
			orderBy = append(orderBy, SqlSorting{term, direction == "ASC"})
		}
	}

	// limit
	limit := -1
	if s := selectStmt.Limit; s != nil {
		if s.Rowcount != nil {
			limit_s := string(s.Rowcount.(*sqlparser.SQLVal).Val)
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
	return q
}
