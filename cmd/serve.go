package cmd

import (
	"fmt"
	"runtime/debug"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(serveCmd)
}

var serveCmd = &cobra.Command{
	Use:   "serve",
	Short: "serve the site",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
			info, ok := debug.ReadBuildInfo()
	if !ok {
		return
	}
	fmt.Println("Key:\tValue")
	for _, kv := range info.Settings {
		fmt.Println(kv.Key + ":\t" + kv.Value)
	}
		gn.Serve()
	},
}
