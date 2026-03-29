package main

import (
	"context"
	"fmt"
	"os"

	"react-fastapi-admin/go-backend/internal/initialize"
	"react-fastapi-admin/go-backend/internal/seed"
)

func main() {
	runtime, err := initialize.InitRuntime()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer runtime.Close()

	if err := seed.Run(context.Background(), runtime.Config, runtime.Logger, runtime.DB); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println("seed completed")
}
