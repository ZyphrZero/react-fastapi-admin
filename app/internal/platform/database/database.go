package database

import (
	"fmt"
	"log/slog"

	"gorm.io/driver/mysql"
	"gorm.io/driver/postgres"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
	gormlogger "gorm.io/gorm/logger"

	"react-go-admin/app/internal/config"
)

func Open(cfg *config.Config, logger *slog.Logger) (*gorm.DB, error) {
	dialector, err := buildDialector(cfg)
	if err != nil {
		return nil, err
	}

	logLevel := gormlogger.Warn
	if cfg.Debug {
		logLevel = gormlogger.Info
	}

	db, err := gorm.Open(dialector, &gorm.Config{
		Logger: gormlogger.Default.LogMode(logLevel),
	})
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	if logger != nil {
		logger.Info("database connected", "driver", cfg.DBConnection)
	}

	return db, nil
}

func buildDialector(cfg *config.Config) (gorm.Dialector, error) {
	switch cfg.DBConnection {
	case "sqlite":
		return sqlite.Open(cfg.DatabasePath()), nil
	case "mysql":
		dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local",
			cfg.DBUsername,
			cfg.DBPassword,
			cfg.DBHost,
			cfg.DBPort,
			cfg.DBDatabase,
		)
		return mysql.Open(dsn), nil
	case "postgres":
		dsn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable TimeZone=Asia/Shanghai",
			cfg.DBHost,
			cfg.DBPort,
			cfg.DBUsername,
			cfg.DBPassword,
			cfg.DBDatabase,
		)
		return postgres.Open(dsn), nil
	default:
		return nil, fmt.Errorf("unsupported database connection: %s", cfg.DBConnection)
	}
}
