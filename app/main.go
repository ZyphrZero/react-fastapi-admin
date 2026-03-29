package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"react-go-admin/app/internal/core"
	"react-go-admin/app/internal/initialize"
	"react-go-admin/app/internal/migrate"
	"react-go-admin/app/internal/seed"
)

func main() {
	runtime, err := initializeSystem()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer runtime.Close()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	engine := initialize.Routers(runtime)
	address := fmt.Sprintf("%s:%d", runtime.Config.Host, runtime.Config.Port)
	runtime.Logger.Info("starting server", "addr", address)

	if err := core.RunServer(ctx, runtime.Logger, address, engine); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func initializeSystem() (*initialize.Runtime, error) {
	runtime, err := initialize.InitRuntime()
	if err != nil {
		return nil, err
	}

	if runtime.Config.DisableAutoMigrate {
		runtime.Logger.Info("auto-migrate disabled, skipping bootstrap")
		return runtime, nil
	}

	ctx := context.Background()
	if err := migrate.Up(ctx, runtime.DB); err != nil {
		runtime.Close()
		return nil, err
	}
	if err := seed.Run(ctx, runtime.Config, runtime.Logger, runtime.DB); err != nil {
		runtime.Close()
		return nil, err
	}
	runtime.Logger.Info("auto bootstrap completed")
	return runtime, nil
}
