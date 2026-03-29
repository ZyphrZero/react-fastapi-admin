package logger

import (
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"gopkg.in/natefinch/lumberjack.v2"

	"react-go-admin/app/internal/config"
)

func New(cfg *config.Config) (*slog.Logger, error) {
	logPath := filepath.Join(cfg.BaseDir, cfg.LogsRoot, "server.log")
	if err := os.MkdirAll(filepath.Dir(logPath), 0o755); err != nil {
		return nil, err
	}

	writer := io.MultiWriter(os.Stdout, &lumberjack.Logger{
		Filename:   logPath,
		MaxBackups: 7,
		MaxAge:     7,
		MaxSize:    10,
	})

	level := slog.LevelInfo
	if cfg.Debug {
		level = slog.LevelDebug
	}

	return slog.New(slog.NewJSONHandler(writer, &slog.HandlerOptions{Level: level})), nil
}
