package catalog

import (
	"context"

	"gorm.io/gorm"

	"react-fastapi-admin/go-backend/internal/modules/apis"
)

func Sync(ctx context.Context, db *gorm.DB) error {
	service := apis.NewService(db.WithContext(ctx))
	return service.Refresh()
}
