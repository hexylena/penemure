package cmd

import (
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(newCmd)

}

var newCmd = &cobra.Command{
	Use:   "new",
	Short: "new",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		gn.NewEdit()
	},
}
