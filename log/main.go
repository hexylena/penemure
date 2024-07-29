package log

import "os"
import "log/slog"
// import "runtime/debug"

var logger *slog.Logger
var defined bool = false

// get logger singleton

func initialise() {
	opts := &slog.HandlerOptions{
		Level: slog.LevelDebug,
	}
	var handler = slog.NewTextHandler(os.Stderr, opts)

	logger = slog.New(handler)
	logger.Info("LoggerInitialized")
}

func GetLogger() *slog.Logger {
	if !defined {
		initialise()
		defined = true
	}
	return logger
}

func L(name string) *slog.Logger {
	parent := GetLogger()
	// buildInfo, ok := debug.ReadBuildInfo()
	// if !ok {
	// 	logger.Warn("No build info")
	// }
	child := parent.With(
		slog.Group("pm",
			slog.String("mod", name),
		),
	)
	return child

}
