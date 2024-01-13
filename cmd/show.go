package cmd

import (
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(showCmd)

}

var showCmd = &cobra.Command{
	Use:   "show [note id]",
	Short: "show a note",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		gn.BubbleShow(args[0])
	},
}
