package cmd

import (
	"fmt"
	pmm "github.com/hexylena/pm/models"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(debugCmd)

}

var debugCmd = &cobra.Command{
	Use:   "debug",
	Short: "debug",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		partial := pmm.PartialNoteId(args[0])
		note_id := gn.GetIdByPartial(partial)
		note := gn.GetNoteById(note_id)
		fmt.Println(note)
		_ = note.GetProjectMembers(gn)

                fmt.Println(note.RenderMarkdown())
	},
}
