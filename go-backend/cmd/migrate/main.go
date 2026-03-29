package main

import (
	"context"
	"flag"
	"fmt"
	"os"

	"react-fastapi-admin/go-backend/internal/initialize"
	"react-fastapi-admin/go-backend/internal/migrate"
)

func main() {
	var (
		showStatus = flag.Bool("status", false, "show migration status")
		rollback   = flag.Bool("down", false, "rollback migrations instead of applying them")
		steps      = flag.Int("steps", 1, "number of migrations to roll back when -down is set")
	)
	flag.Parse()

	runtime, err := initialize.InitRuntime()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer runtime.Close()

	ctx := context.Background()
	switch {
	case *showStatus:
		statuses, err := migrate.Statuses(ctx, runtime.DB)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		for _, item := range statuses {
			state := "pending"
			if item.Applied {
				state = "applied"
			}
			fmt.Printf("%d\t%s\t%s\n", item.Version, item.Name, state)
		}
	case *rollback:
		if err := migrate.Down(ctx, runtime.DB, *steps); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Printf("rolled back %d migration(s)\n", *steps)
	default:
		if err := migrate.Up(ctx, runtime.DB); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Println("migrations applied")
	}
}
