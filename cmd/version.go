package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

var echoTimes int

func init() {
	rootCmd.AddCommand(versionCmd)
	versionCmd.Flags().IntVarP(&echoTimes, "times", "t", 1, "times to echo the input")

}

var versionCmd = &cobra.Command{
	Use:   "version <id>",
	Short: "Print the version number of Hugo",
	Long:  `All software has versions. This is Hugo's`,
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("Hugo Static Site Generator v0.9 -- HEAD")
		fmt.Println(args)
		fmt.Println(echoTimes)
	},
}
