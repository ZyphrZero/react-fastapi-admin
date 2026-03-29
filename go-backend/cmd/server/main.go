package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"react-fastapi-admin/go-backend/internal/core"
	"react-fastapi-admin/go-backend/internal/initialize"
)

func main() {
	runtime, err := initialize.InitRuntime()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer runtime.Close()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	engine := initialize.Routers(runtime)
	address := fmt.Sprintf("%s:%d", runtime.Config.Host, runtime.Config.Port)
	runtime.Logger.Info("starting go backend server", "addr", address)
	if err := core.RunServer(ctx, runtime.Logger, address, engine); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
