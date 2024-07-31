package cmd

import (
	pmm "github.com/hexylena/pm/models"
	"fmt"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(authorCmd)

}

var authorCmd = &cobra.Command{
	Use:   "author [note id] [authoree]",
	Short: "author a note",
	Args:  cobra.MinimumNArgs(2),
	Run: func(cmd *cobra.Command, args []string) {
		partial := pmm.PartialNoteId(args[0])
		note_id, err := gn.GetIdByPartial(partial)
		if err != nil {
			fmt.Println(err)
			return
		}
		note := gn.GetNoteById(note_id)
		note.RemoveMetaTag("Author")
		note.AddMetaTag("Author", args[1])
	},
}
