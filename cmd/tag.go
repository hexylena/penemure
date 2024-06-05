package cmd

import (
	"fmt"
	pmm "github.com/hexylena/pm/models"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(tagCmd)

}

var tagCmd = &cobra.Command{
	Use:   "tag <note> <tag>",
	Short: "tag a note",
	Args:  cobra.MaximumNArgs(2),
	Run: func(cmd *cobra.Command, args []string) {
		partial := pmm.PartialNoteId(args[0])
		note_id, err := gn.GetIdByPartial(partial)
		if err != nil {
			fmt.Println(err)
			return
		}
		note := gn.GetNoteById(note_id)

		m, err := note.GetMetaKey("Tags")
		if err != nil {
			m = &pmm.Meta{Type: "text", Title: "Tags", Value: []string{args[1]}}
			note.Meta = append(note.Meta, m)
		} else {
			m.Value = append(m.Value.([]interface{}), args[1])
		}
		note.Touch()
	},
}
