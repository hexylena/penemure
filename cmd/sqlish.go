package cmd

import (
	"github.com/spf13/cobra"
	"fmt"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/lipgloss/table"
	"github.com/hexylena/pm/sqlish"
	"strings"
	"os"
)

const (
	purple    = lipgloss.Color("99")
	gray      = lipgloss.Color("245")
	lightGray = lipgloss.Color("241")
)

func init() {
	rootCmd.AddCommand(sqlishCmd)

}

var sqlishCmd = &cobra.Command{
	Use:   "sqlish [query]",
	Short: "query items in the project, optionally filtering",
	Args:  cobra.MinimumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		q := strings.Join(args, " ")
		ans := sqlish.ParseSqlQuery(q)

		flattened_notes := []map[string]string{}
		for _, note := range gn.GetNotes() {
			flattened_notes = append(flattened_notes, note.Flatten())
		}
		results := ans.FilterDocuments(flattened_notes)
		// headers := ans.GetFields()
		// gn.BubblePrint()

		for group, rows := range results {
			fmt.Println(group)

			re := lipgloss.NewRenderer(os.Stdout)
			var (
				// HeaderStyle is the lipgloss style used for the table headers.
				HeaderStyle = re.NewStyle().Foreground(purple).Bold(true).Align(lipgloss.Center)
				// CellStyle is the base lipgloss style used for the table rows.
				CellStyle = re.NewStyle().Padding(0, 1).Width(18)
				// OddRowStyle is the lipgloss style used for odd-numbered table rows.
				OddRowStyle = CellStyle.Copy().Foreground(gray)
				// EvenRowStyle is the lipgloss style used for even-numbered table rows.
				EvenRowStyle = CellStyle.Copy().Foreground(lightGray)
				// BorderStyle is the lipgloss style used for the table border.
				// BorderStyle = lipgloss.NewStyle().Foreground(purple)
			)

			t := table.New().
				Border(lipgloss.NormalBorder()).
				BorderStyle(lipgloss.NewStyle().Foreground(lipgloss.Color("99"))).
				StyleFunc(func(row, col int) lipgloss.Style {
					switch {
					case row == 0:
						return HeaderStyle
					case row%2 == 0:
						return EvenRowStyle
					default:
						return OddRowStyle
					}
				}).
				// Headers(headers...).
				Rows(rows...)

			fmt.Println(t)
		}
	},
}
