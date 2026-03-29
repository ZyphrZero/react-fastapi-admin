package router

import (
	"log/slog"
	"net/http"
	"path/filepath"
	"regexp"
	"time"

	gincors "github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"

	"react-fastapi-admin/go-backend/internal/config"
	"react-fastapi-admin/go-backend/internal/modules/auditlog"
	"react-fastapi-admin/go-backend/internal/modules/apis"
	"react-fastapi-admin/go-backend/internal/modules/base"
	"react-fastapi-admin/go-backend/internal/modules/roles"
	"react-fastapi-admin/go-backend/internal/modules/systemsettings"
	"react-fastapi-admin/go-backend/internal/modules/upload"
	"react-fastapi-admin/go-backend/internal/modules/users"
	"react-fastapi-admin/go-backend/internal/platform/response"
)

func New(
	cfg *config.Config,
	logger *slog.Logger,
	baseService *base.Service,
	baseHandler *base.Handler,
	auditLogHandler *auditlog.Handler,
	usersHandler *users.Handler,
	rolesHandler *roles.Handler,
	apisHandler *apis.Handler,
	systemSettingsHandler *systemsettings.Handler,
	uploadHandler *upload.Handler,
) *gin.Engine {
	if cfg.IsProduction() {
		gin.SetMode(gin.ReleaseMode)
	} else {
		gin.SetMode(gin.DebugMode)
	}

	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(gincors.New(buildCORSConfig(cfg)))
	r.Use(requestLogger(logger))
	r.StaticFS("/static", gin.Dir(filepath.Join(cfg.BaseDir, "storage"), false))

	r.GET("/health", func(c *gin.Context) {
		response.Success(c.Writer, map[string]interface{}{
			"status":      "ok",
			"app":         cfg.ProjectName,
			"version":     cfg.Version,
			"environment": cfg.AppEnv,
		}, "成功", nil)
	})

	baseGroup := r.Group("/api/v1/base")
	baseGroup.POST("/access_token", gin.WrapF(baseHandler.Login))
	baseGroup.POST("/refresh_token", gin.WrapF(baseHandler.Refresh))
	baseGroup.GET("/app_meta", gin.WrapF(baseHandler.AppMeta))

	authGroup := baseGroup.Group("")
	authGroup.Use(ginAuthMiddleware(baseHandler))
	authGroup.GET("/userinfo", gin.WrapF(baseHandler.UserInfo))
	authGroup.GET("/password_policy", gin.WrapF(baseHandler.PasswordPolicy))
	authGroup.POST("/update_password", gin.WrapF(baseHandler.UpdatePassword))
	authGroup.POST("/update_profile", gin.WrapF(baseHandler.UpdateProfile))
	authGroup.POST("/logout", gin.WrapF(baseHandler.Logout))
	authGroup.GET("/usermenu", gin.WrapF(baseHandler.UserMenu))
	authGroup.GET("/userapi", gin.WrapF(baseHandler.UserAPI))
	authGroup.GET("/overview", gin.WrapF(baseHandler.Overview))
	authGroup.POST("/upload_avatar", gin.WrapF(uploadHandler.UploadAvatar))

	userGroup := r.Group("/api/v1/user")
	userGroup.Use(ginAuthMiddleware(baseHandler), ginPermissionMiddleware(baseService))
	userGroup.GET("/list", gin.WrapF(usersHandler.List))
	userGroup.GET("/get", gin.WrapF(usersHandler.Get))
	userGroup.POST("/create", gin.WrapF(usersHandler.Create))
	userGroup.POST("/update", gin.WrapF(usersHandler.Update))
	userGroup.DELETE("/delete", gin.WrapF(usersHandler.Delete))
	userGroup.POST("/reset_password", gin.WrapF(usersHandler.ResetPassword))

	roleGroup := r.Group("/api/v1/role")
	roleGroup.Use(ginAuthMiddleware(baseHandler), ginPermissionMiddleware(baseService))
	roleGroup.GET("/list", gin.WrapF(rolesHandler.List))
	roleGroup.GET("/get", gin.WrapF(rolesHandler.Get))
	roleGroup.GET("/permission_options", gin.WrapF(rolesHandler.PermissionOptions))
	roleGroup.POST("/create", gin.WrapF(rolesHandler.Create))
	roleGroup.POST("/update", gin.WrapF(rolesHandler.Update))
	roleGroup.DELETE("/delete", gin.WrapF(rolesHandler.Delete))

	apiGroup := r.Group("/api/v1/api")
	apiGroup.Use(ginAuthMiddleware(baseHandler), ginPermissionMiddleware(baseService))
	apiGroup.GET("/list", gin.WrapF(apisHandler.List))
	apiGroup.GET("/get", gin.WrapF(apisHandler.Get))
	apiGroup.POST("/update", gin.WrapF(apisHandler.Update))
	apiGroup.DELETE("/delete", gin.WrapF(apisHandler.Delete))
	apiGroup.POST("/refresh", gin.WrapF(apisHandler.Refresh))
	apiGroup.GET("/tags", gin.WrapF(apisHandler.Tags))

	auditLogGroup := r.Group("/api/v1/auditlog")
	auditLogGroup.Use(ginAuthMiddleware(baseHandler), ginPermissionMiddleware(baseService))
	auditLogGroup.GET("/list", gin.WrapF(auditLogHandler.List))
	auditLogGroup.GET("/detail/:log_id", gin.WrapF(auditLogHandler.Detail))
	auditLogGroup.DELETE("/delete/:log_id", gin.WrapF(auditLogHandler.Delete))
	auditLogGroup.DELETE("/batch_delete", gin.WrapF(auditLogHandler.BatchDelete))
	auditLogGroup.DELETE("/clear", gin.WrapF(auditLogHandler.Clear))
	auditLogGroup.POST("/export", gin.WrapF(auditLogHandler.Export))
	auditLogGroup.GET("/download/:filename", gin.WrapF(auditLogHandler.Download))
	auditLogGroup.GET("/statistics", gin.WrapF(auditLogHandler.Statistics))

	systemSettingsGroup := r.Group("/api/v1/system_settings")
	systemSettingsGroup.Use(ginAuthMiddleware(baseHandler))
	systemSettingsGroup.GET("/application", gin.WrapF(systemSettingsHandler.GetApplication))
	systemSettingsGroup.POST("/application", gin.WrapF(systemSettingsHandler.UpdateApplication))
	systemSettingsGroup.GET("/logging", gin.WrapF(systemSettingsHandler.GetLogging))
	systemSettingsGroup.POST("/logging", gin.WrapF(systemSettingsHandler.UpdateLogging))
	systemSettingsGroup.GET("/security", gin.WrapF(systemSettingsHandler.GetSecurity))
	systemSettingsGroup.POST("/security", gin.WrapF(systemSettingsHandler.UpdateSecurity))
	systemSettingsGroup.GET("/storage", gin.WrapF(systemSettingsHandler.GetStorage))
	systemSettingsGroup.POST("/storage", gin.WrapF(systemSettingsHandler.UpdateStorage))

	uploadGroup := r.Group("/api/v1/upload")
	uploadGroup.Use(ginAuthMiddleware(baseHandler), ginPermissionMiddleware(baseService))
	uploadGroup.POST("/image", gin.WrapF(uploadHandler.UploadImage))
	uploadGroup.POST("/files", gin.WrapF(uploadHandler.UploadFiles))
	uploadGroup.GET("/list", gin.WrapF(uploadHandler.ListFiles))
	uploadGroup.DELETE("/delete", gin.WrapF(uploadHandler.DeleteFile))
	uploadGroup.POST("/set-public-acl", gin.WrapF(uploadHandler.SetPublicACL))

	return r
}

func requestLogger(logger *slog.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		c.Next()
		logger.Info("http request",
			"method", c.Request.Method,
			"path", c.Request.URL.Path,
			"status", c.Writer.Status(),
			"duration_ms", time.Since(start).Milliseconds(),
		)
	}
}

func ginAuthMiddleware(baseHandler *base.Handler) gin.HandlerFunc {
	return func(c *gin.Context) {
		called := false
		next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			called = true
			c.Request = r
		})
		baseHandler.AuthMiddleware(next).ServeHTTP(c.Writer, c.Request)
		if !called {
			c.Abort()
			return
		}
		c.Next()
	}
}

func ginPermissionMiddleware(baseService *base.Service) gin.HandlerFunc {
	return func(c *gin.Context) {
		user, ok := base.CurrentUserFromContext(c.Request.Context())
		if !ok {
			response.Error(c.Writer, http.StatusUnauthorized, "未授权访问", nil)
			c.Abort()
			return
		}
		routePath := c.FullPath()
		if routePath == "" {
			routePath = c.Request.URL.Path
		}
		routePath = normalizePermissionPath(routePath)
		if err := baseService.CheckPermission(c.Request.Context(), user, c.Request.Method, routePath); err != nil {
			response.Error(c.Writer, http.StatusForbidden, err.Error(), nil)
			c.Abort()
			return
		}
		c.Next()
	}
}

var ginParamPattern = regexp.MustCompile(`:([A-Za-z0-9_]+)`)

func normalizePermissionPath(path string) string {
	return ginParamPattern.ReplaceAllString(path, `{$1}`)
}

func buildCORSConfig(cfg *config.Config) gincors.Config {
	corsConfig := gincors.Config{
		AllowMethods:     cfg.CORSAllowMethods,
		AllowHeaders:     cfg.CORSAllowHeaders,
		AllowCredentials: cfg.CORSAllowCredentials,
		MaxAge:           300 * time.Second,
	}
	if len(cfg.CORSOrigins) == 1 && cfg.CORSOrigins[0] == "*" {
		corsConfig.AllowOriginFunc = func(origin string) bool {
			return true
		}
		return corsConfig
	}
	corsConfig.AllowOrigins = cfg.CORSOrigins
	return corsConfig
}
