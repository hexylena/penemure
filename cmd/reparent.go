package cmd

import (
	"fmt"
	pmm "github.com/hexylena/pm/models"
	"github.com/spf13/cobra"
)

var replace bool

func init() {
	rootCmd.AddCommand(reparentCmd)
	reparentCmd.Flags().BoolVarP(&replace, "replace", "r", false, "replace, rather than adding")
}

var reparentCmd = &cobra.Command{
	Use:   "reparent [note id] [new parent id]",
	Short: "reparent a note",
	// Exactly two args
	Args: cobra.MinimumNArgs(2),
	Run: func(cmd *cobra.Command, args []string) {
		partial := pmm.PartialNoteId(args[0])
		note_id, err := gn.GetIdByPartial(partial)
		note := gn.GetNoteById(note_id)
		if err != nil {
			fmt.Println(err)
			return
		}

		fmt.Printf("Reparenting %s (%s)", note.Title, note.NoteId)

		new_parent_partial := pmm.PartialNoteId(args[1])
		new_parent_id, err := gn.GetIdByPartial(new_parent_partial)
		new_parent := gn.GetNoteById(new_parent_id)
		if err != nil {
			fmt.Println(err)
			return
		}
		fmt.Printf(" to %s (%s)\n", new_parent.Title, new_parent.NoteId)

		if replace {
			note.SetParent(new_parent_id)
			fmt.Printf("Replacing current parents (%s)\n", note.Parents)
		} else {
			note.AddParent(new_parent_id)
			fmt.Printf("Appending to current parents (%s)\n", note.Parents)
		}
	},
}
