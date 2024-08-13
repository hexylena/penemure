// Package models provides functionality for working with models.
package models

import (
	"fmt"
	"bytes"
	"html"
	"os/exec"
	"strings"
)

type Plugin struct {
}

func (p Plugin) Render(plug, value string) string {
	logger.Info("RenderPlugin", "plug", plug, "value", value)
	switch plug {
	case "git.commit.embed":
		out := "<pre style=\"max-height: 20em; overflow: auto;\"><code language=\"console\">"
		// get output of `git show value`
		cmd := exec.Command("git", "show", value)
		out += "$ git show " + value + "\n"
		var stderr bytes.Buffer
		cmd.Stderr = &stderr
		output, err := cmd.Output()

		if err != nil {
			out += html.EscapeString(strings.TrimSpace(fmt.Sprintf("%s: %s", err, stderr.String())))
		}
		// make output safe for embedding in HTML:
		// - escape HTML entities
		// - remove leading and trailing whitespace

		out += html.EscapeString(strings.TrimSpace(string(output)))
		out += "</code></pre>"
		return out
	default:
		return value
	}
}
