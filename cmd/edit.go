package cmd

import (
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
		gn.Edit(args[0])
	},
}
