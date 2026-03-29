package core

import (
	"context"
	"log/slog"
	"time"

	"github.com/gin-gonic/gin"
)

// RunServer starts the HTTP server and handles graceful shutdown.
func RunServer(ctx context.Context, logger *slog.Logger, address string, engine *gin.Engine) error {
	return initServer(ctx, logger, address, engine, 10*time.Second, 10*time.Second)
}
