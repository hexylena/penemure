package cmd

import (
	pmm "github.com/hexylena/pm/models"
	pma "github.com/hexylena/pm/adapter"
	"fmt"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(rmCmd)

}

var rmCmd = &cobra.Command{
	Use:   "rm",
	Short: "rm",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		partial := pmm.PartialNoteId(args[0])
		note_id := gn.GetIdByPartial(partial)
		fmt.Println("REMOVING THE FOLLOWING NOTE")
		gn.BubbleShow(partial)
		pma.DeleteNote(gn, note_id)
	},
}
