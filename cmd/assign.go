package cmd

import (
	"fmt"

	pmm "github.com/hexylena/pm/models"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(assignCmd)

}

var assignCmd = &cobra.Command{
	Use:   "assign [note id] [assignee]",
	Short: "assign a note",
	Args:  cobra.MinimumNArgs(2),
	Run: func(cmd *cobra.Command, args []string) {
		partial := pmm.PartialNoteId(args[0])
		note_id, err := gn.GetIdByPartial(partial)
		if err != nil {
			fmt.Println(err)
			return
		}
		note := gn.GetNoteByID(note_id)
		note.AddMetaTag("assignee", args[1])
	},
}
