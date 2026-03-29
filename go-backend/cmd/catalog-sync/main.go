package main

import (
	"context"
	"fmt"
	"os"

	"react-fastapi-admin/go-backend/internal/catalog"
	"react-fastapi-admin/go-backend/internal/initialize"
)

func main() {
	runtime, err := initialize.InitRuntime()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer runtime.Close()

	if err := catalog.Sync(context.Background(), runtime.DB); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println("catalog synced")
}
