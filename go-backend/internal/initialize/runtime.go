package initialize

import (
	"log/slog"

	"gorm.io/gorm"

	"react-fastapi-admin/go-backend/internal/config"
	"react-fastapi-admin/go-backend/internal/modules/auditlog"
	"react-fastapi-admin/go-backend/internal/modules/apis"
	"react-fastapi-admin/go-backend/internal/modules/base"
	"react-fastapi-admin/go-backend/internal/modules/roles"
	"react-fastapi-admin/go-backend/internal/modules/systemsettings"
	"react-fastapi-admin/go-backend/internal/modules/upload"
	"react-fastapi-admin/go-backend/internal/modules/users"
	"react-fastapi-admin/go-backend/internal/platform/database"
	applogger "react-fastapi-admin/go-backend/internal/platform/logger"
)

// Runtime contains the initialized Go backend dependencies.
type Runtime struct {
	Config                *config.Config
	Logger                *slog.Logger
	DB                    *gorm.DB
	BaseService           *base.Service
	BaseHandler           *base.Handler
	AuditLogHandler       *auditlog.Handler
	UsersHandler          *users.Handler
	RolesHandler          *roles.Handler
	APIsHandler           *apis.Handler
	SystemSettingsHandler *systemsettings.Handler
	UploadHandler         *upload.Handler
}

// InitRuntime initializes config, logger, database, and module handlers.
func InitRuntime() (*Runtime, error) {
	cfg, err := config.Load()
	if err != nil {
		return nil, err
	}

	logger, err := applogger.New(cfg)
	if err != nil {
		return nil, err
	}

	db, err := database.Open(cfg, logger)
	if err != nil {
		return nil, err
	}

	baseService := base.NewService(cfg, db)
	baseHandler := base.NewHandler(baseService)

	return &Runtime{
		Config:                cfg,
		Logger:                logger,
		DB:                    db,
		BaseService:           baseService,
		BaseHandler:           baseHandler,
		AuditLogHandler:       auditlog.NewHandler(auditlog.NewService(cfg, db)),
		UsersHandler:          users.NewHandler(users.NewService(db, baseService)),
		RolesHandler:          roles.NewHandler(roles.NewService(db, baseService)),
		APIsHandler:           apis.NewHandler(apis.NewService(db)),
		SystemSettingsHandler: systemsettings.NewHandler(systemsettings.NewService(cfg, db)),
		UploadHandler:         upload.NewHandler(upload.NewService(cfg, db)),
	}, nil
}

// Close releases the underlying SQL connection.
func (rt *Runtime) Close() error {
	if rt == nil || rt.DB == nil {
		return nil
	}
	sqlDB, err := rt.DB.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}
