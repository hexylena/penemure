package cmd

import (
	pmm "github.com/hexylena/pm/models"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(editCmd)

}

var editCmd = &cobra.Command{
	Use:   "edit [note id]",
	Short: "edit a note",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		partial := pmm.PartialNoteId(args[0])
		gn.Edit(partial)
	},
}
