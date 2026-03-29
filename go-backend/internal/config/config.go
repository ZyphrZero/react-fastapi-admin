package config

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/joho/godotenv"
)

type Config struct {
	AppEnv                      string
	Version                     string
	AppTitle                    string
	ProjectName                 string
	AppDescription              string
	Debug                       bool
	Host                        string
	Port                        int
	BaseDir                     string
	LogsRoot                    string
	LogRetentionDays            int
	LogRotation                 string
	LogMaxFileSize              string
	LogEnableAccessLog          bool
	SecretKey                   string
	JWTAlgorithm                string
	JWTAccessTokenExpireMinutes int
	JWTRefreshTokenExpireDays   int
	RefreshTokenCookieName      string
	RefreshTokenCookieSecure    bool
	RefreshTokenCookieSameSite  string
	CORSOrigins                 []string
	CORSAllowCredentials        bool
	CORSAllowMethods            []string
	CORSAllowHeaders            []string
	DBConnection                string
	DBFile                      string
	DBHost                      string
	DBPort                      int
	DBUsername                  string
	DBPassword                  string
	DBDatabase                  string
	PasswordMinLength           int
	PasswordRequireUppercase    bool
	PasswordRequireLowercase    bool
	PasswordRequireDigits       bool
	PasswordRequireSpecial      bool
	NotificationPosition        string
	NotificationDuration        int
	NotificationVisibleToasts   int
	InitialAdminUsername        string
	InitialAdminEmail           string
	InitialAdminNickname        string
	InitialAdminPassword        string
}

var (
	loadOnce sync.Once
	loaded   *Config
	loadErr  error
)

func Load() (*Config, error) {
	loadOnce.Do(func() {
		root, err := findProjectRoot()
		if err != nil {
			loadErr = err
			return
		}

		_ = godotenv.Load(filepath.Join(root, ".env"))

		cfg := &Config{
			AppEnv:                      getEnv("APP_ENV", "dev"),
			Version:                     getEnv("VERSION", "0.1.0"),
			AppTitle:                    getEnv("APP_TITLE", "React FastAPI Admin"),
			ProjectName:                 getEnv("PROJECT_NAME", "React FastAPI Admin"),
			AppDescription:              getEnv("APP_DESCRIPTION", "React FastAPI Admin Description"),
			Debug:                       getEnvBool("DEBUG", false),
			Host:                        getEnv("HOST", "0.0.0.0"),
			Port:                        getEnvInt("PORT", 9999),
			BaseDir:                     root,
			LogsRoot:                    getEnv("LOGS_ROOT", "app/logs"),
			LogRetentionDays:            getEnvInt("LOG_RETENTION_DAYS", 7),
			LogRotation:                 getEnv("LOG_ROTATION", "1 day"),
			LogMaxFileSize:              getEnv("LOG_MAX_FILE_SIZE", "10 MB"),
			LogEnableAccessLog:          getEnvBool("LOG_ENABLE_ACCESS_LOG", true),
			SecretKey:                   strings.TrimSpace(os.Getenv("SECRET_KEY")),
			JWTAlgorithm:                getEnv("JWT_ALGORITHM", "HS256"),
			JWTAccessTokenExpireMinutes: getEnvInt("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 15),
			JWTRefreshTokenExpireDays:   getEnvInt("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7),
			RefreshTokenCookieName:      getEnv("REFRESH_TOKEN_COOKIE_NAME", "refresh_token"),
			CORSOrigins:                 getEnvList("CORS_ORIGINS", []string{"*"}),
			CORSAllowCredentials:        getEnvBool("CORS_ALLOW_CREDENTIALS", true),
			CORSAllowMethods:            getEnvList("CORS_ALLOW_METHODS", []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}),
			CORSAllowHeaders:            getEnvList("CORS_ALLOW_HEADERS", []string{"*"}),
			DBConnection:                getEnv("DB_CONNECTION", "sqlite"),
			DBFile:                      getEnv("DB_FILE", "db.sqlite3"),
			DBHost:                      getEnv("DB_HOST", "localhost"),
			DBPort:                      getEnvInt("DB_PORT", 3306),
			DBUsername:                  getEnv("DB_USERNAME", "root"),
			DBPassword:                  os.Getenv("DB_PASSWORD"),
			DBDatabase:                  getEnv("DB_DATABASE", "fastapi_admin"),
			PasswordMinLength:           getEnvInt("PASSWORD_MIN_LENGTH", 8),
			PasswordRequireUppercase:    getEnvBool("PASSWORD_REQUIRE_UPPERCASE", true),
			PasswordRequireLowercase:    getEnvBool("PASSWORD_REQUIRE_LOWERCASE", true),
			PasswordRequireDigits:       getEnvBool("PASSWORD_REQUIRE_DIGITS", true),
			PasswordRequireSpecial:      getEnvBool("PASSWORD_REQUIRE_SPECIAL", true),
			NotificationPosition:        getEnv("NOTIFICATION_POSITION", "top-right"),
			NotificationDuration:        getEnvInt("NOTIFICATION_DURATION", 4000),
			NotificationVisibleToasts:   getEnvInt("NOTIFICATION_VISIBLE_TOASTS", 3),
			InitialAdminUsername:        getEnv("INITIAL_ADMIN_USERNAME", "admin"),
			InitialAdminEmail:           getEnv("INITIAL_ADMIN_EMAIL", "admin@example.com"),
			InitialAdminNickname:        getEnv("INITIAL_ADMIN_NICKNAME", "admin"),
			InitialAdminPassword:        os.Getenv("INITIAL_ADMIN_PASSWORD"),
		}

		cfg.RefreshTokenCookieSameSite = strings.ToLower(getEnv("REFRESH_TOKEN_COOKIE_SAMESITE", "lax"))
		cfg.RefreshTokenCookieSecure = getEnvBool("REFRESH_TOKEN_COOKIE_SECURE", cfg.IsProduction())

		if cfg.SecretKey == "" {
			if cfg.IsProduction() {
				loadErr = fmt.Errorf("SECRET_KEY must be configured in production")
				return
			}

			secret, err := randomSecret()
			if err != nil {
				loadErr = err
				return
			}
			cfg.SecretKey = secret
		}

		if len(cfg.SecretKey) < 32 {
			loadErr = fmt.Errorf("SECRET_KEY must be at least 32 characters")
			return
		}

		loaded = cfg
	})

	return loaded, loadErr
}

func (c Config) IsProduction() bool {
	return strings.EqualFold(c.AppEnv, "prod")
}

func (c Config) DatabasePath() string {
	return filepath.Join(c.BaseDir, c.DBFile)
}

func findProjectRoot() (string, error) {
	wd, err := os.Getwd()
	if err != nil {
		return "", err
	}

	dir := wd
	for {
		if _, err := os.Stat(filepath.Join(dir, ".env.example")); err == nil {
			return dir, nil
		}

		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("could not locate project root from %s", wd)
		}
		dir = parent
	}
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok && strings.TrimSpace(value) != "" {
		return strings.TrimSpace(value)
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	value, ok := os.LookupEnv(key)
	if !ok || strings.TrimSpace(value) == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(strings.TrimSpace(value))
	if err != nil {
		return fallback
	}
	return parsed
}

func getEnvBool(key string, fallback bool) bool {
	value, ok := os.LookupEnv(key)
	if !ok || strings.TrimSpace(value) == "" {
		return fallback
	}
	parsed, err := strconv.ParseBool(strings.TrimSpace(value))
	if err != nil {
		return fallback
	}
	return parsed
}

func getEnvList(key string, fallback []string) []string {
	value, ok := os.LookupEnv(key)
	if !ok || strings.TrimSpace(value) == "" {
		return fallback
	}

	parts := strings.Split(value, ",")
	items := make([]string, 0, len(parts))
	for _, part := range parts {
		item := strings.TrimSpace(part)
		if item != "" {
			items = append(items, item)
		}
	}
	if len(items) == 0 {
		return fallback
	}
	return items
}

func randomSecret() (string, error) {
	buf := make([]byte, 32)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return hex.EncodeToString(buf), nil
}
