package initialize

import (
	"github.com/gin-gonic/gin"

	"react-fastapi-admin/go-backend/internal/http/router"
)

// Routers builds the Gin engine from the initialized runtime.
func Routers(rt *Runtime) *gin.Engine {
	return router.New(
		rt.Config,
		rt.Logger,
		rt.BaseService,
		rt.BaseHandler,
		rt.AuditLogHandler,
		rt.UsersHandler,
		rt.RolesHandler,
		rt.APIsHandler,
		rt.SystemSettingsHandler,
		rt.UploadHandler,
	)
}
