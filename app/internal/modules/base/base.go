package base

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"sort"
	"strings"
	"time"

	"gorm.io/gorm"

	"react-go-admin/app/internal/config"
	"react-go-admin/app/internal/platform/auth"
	"react-go-admin/app/internal/platform/database"
	"react-go-admin/app/internal/platform/password"
	"react-go-admin/app/internal/platform/response"
)

type Service struct {
	cfg    *config.Config
	db     *gorm.DB
	auth   *auth.Manager
	policy password.Policy
}

type Handler struct {
	service *Service
}

type credentialsRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type updatePasswordRequest struct {
	OldPassword string `json:"old_password"`
	NewPassword string `json:"new_password"`
}

type updateProfileRequest struct {
	Nickname *string `json:"nickname"`
	Avatar   *string `json:"avatar"`
	Email    *string `json:"email"`
	Phone    *string `json:"phone"`
}

type currentUserKey struct{}

type applicationSettings struct {
	AppTitle                  string  `json:"app_title"`
	ProjectName               string  `json:"project_name"`
	AppDescription            string  `json:"app_description"`
	Debug                     bool    `json:"debug"`
	LoginPageImageURL         string  `json:"login_page_image_url"`
	LoginPageImageMode        string  `json:"login_page_image_mode"`
	LoginPageImageZoom        float64 `json:"login_page_image_zoom"`
	LoginPageImagePositionX   float64 `json:"login_page_image_position_x"`
	LoginPageImagePositionY   float64 `json:"login_page_image_position_y"`
	NotificationPosition      string  `json:"notification_position"`
	NotificationDuration      int     `json:"notification_duration"`
	NotificationVisibleToasts int     `json:"notification_visible_toasts"`
}

type securitySettings struct {
	PasswordMinLength        int    `json:"password_min_length"`
	PasswordRequireUppercase bool   `json:"password_require_uppercase"`
	PasswordRequireLowercase bool   `json:"password_require_lowercase"`
	PasswordRequireDigits    bool   `json:"password_require_digits"`
	PasswordRequireSpecial   bool   `json:"password_require_special"`
	RateLimitEnabled         bool   `json:"rate_limit_enabled"`
	RateLimitMaxRequests     int    `json:"rate_limit_max_requests"`
	RateLimitWindowSeconds   int    `json:"rate_limit_window_seconds"`
	IPWhitelist              string `json:"ip_whitelist"`
}

type trendRow struct {
	Date  string `gorm:"column:date"`
	Count int    `gorm:"column:count"`
}

type chartRow struct {
	Module string `gorm:"column:module"`
	Status int    `gorm:"column:status"`
}

func NewService(cfg *config.Config, db *gorm.DB) *Service {
	return &Service{
		cfg:    cfg,
		db:     db,
		auth:   auth.NewManager(cfg),
		policy: password.NewPolicy(cfg),
	}
}

func NewHandler(service *Service) *Handler {
	return &Handler{service: service}
}

func (s *Service) Login(ctx context.Context, req credentialsRequest) (map[string]string, string, error) {
	var user database.User
	if err := s.db.WithContext(ctx).Where("username = ?", req.Username).First(&user).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, "", fmt.Errorf("用户名或密码错误")
		}
		return nil, "", err
	}

	if !password.Verify(req.Password, user.Password) {
		return nil, "", fmt.Errorf("用户名或密码错误")
	}
	if !user.IsActive {
		return nil, "", fmt.Errorf("用户已被禁用")
	}

	refreshTokenJTI := randomID()
	now := time.Now()
	user.LastLogin = &now
	user.RefreshTokenJTI = &refreshTokenJTI
	if err := s.db.WithContext(ctx).Model(&user).Updates(map[string]interface{}{
		"last_login":        now,
		"refresh_token_jti": refreshTokenJTI,
		"updated_at":        now,
	}).Error; err != nil {
		return nil, "", err
	}

	accessToken, err := s.auth.CreateAccessToken(user.ID, user.Username, user.IsSuperuser, user.SessionVersion)
	if err != nil {
		return nil, "", err
	}
	refreshToken, err := s.auth.CreateRefreshToken(user.ID, user.SessionVersion, refreshTokenJTI)
	if err != nil {
		return nil, "", err
	}

	return map[string]string{
		"access_token": accessToken,
		"username":     user.Username,
		"token_type":   "bearer",
	}, refreshToken, nil
}

func (s *Service) Refresh(ctx context.Context, refreshToken string) (map[string]string, string, error) {
	claims, err := s.auth.Parse(refreshToken, "refresh")
	if err != nil {
		return nil, "", fmt.Errorf("无效的刷新令牌")
	}

	user, err := s.findUser(ctx, claims.UserID)
	if err != nil {
		return nil, "", err
	}
	if !user.IsActive {
		return nil, "", fmt.Errorf("用户已被禁用")
	}
	if user.SessionVersion != claims.SessionVersion {
		return nil, "", fmt.Errorf("登录状态已失效，请重新登录")
	}
	if user.RefreshTokenJTI == nil || *user.RefreshTokenJTI != claims.ID {
		return nil, "", fmt.Errorf("刷新令牌已失效，请重新登录")
	}

	refreshTokenJTI := randomID()
	if err := s.db.WithContext(ctx).Model(user).Updates(map[string]interface{}{
		"refresh_token_jti": refreshTokenJTI,
		"updated_at":        time.Now(),
	}).Error; err != nil {
		return nil, "", err
	}

	accessToken, err := s.auth.CreateAccessToken(user.ID, user.Username, user.IsSuperuser, user.SessionVersion)
	if err != nil {
		return nil, "", err
	}
	newRefreshToken, err := s.auth.CreateRefreshToken(user.ID, user.SessionVersion, refreshTokenJTI)
	if err != nil {
		return nil, "", err
	}

	return map[string]string{
		"access_token": accessToken,
		"username":     user.Username,
		"token_type":   "bearer",
	}, newRefreshToken, nil
}

func (s *Service) Authenticate(ctx context.Context, authorization string) (*database.User, error) {
	token, err := extractBearerToken(authorization)
	if err != nil {
		return nil, err
	}

	claims, err := s.auth.Parse(token, "access")
	if err != nil {
		return nil, fmt.Errorf("认证失败")
	}

	user, err := s.findUser(ctx, claims.UserID)
	if err != nil {
		return nil, err
	}
	if !user.IsActive {
		return nil, fmt.Errorf("用户已被禁用")
	}
	if user.SessionVersion != claims.SessionVersion {
		return nil, fmt.Errorf("登录状态已失效，请重新登录")
	}

	return user, nil
}

func (s *Service) AppMeta(ctx context.Context) map[string]interface{} {
	settings := s.loadApplicationSettings(ctx)
	return map[string]interface{}{
		"app_title":                   settings.AppTitle,
		"project_name":                settings.ProjectName,
		"app_description":             settings.AppDescription,
		"login_page_image_url":        settings.LoginPageImageURL,
		"login_page_image_mode":       settings.LoginPageImageMode,
		"login_page_image_zoom":       settings.LoginPageImageZoom,
		"login_page_image_position_x": settings.LoginPageImagePositionX,
		"login_page_image_position_y": settings.LoginPageImagePositionY,
		"notification_position":       settings.NotificationPosition,
		"notification_duration":       settings.NotificationDuration,
		"notification_visible_toasts": settings.NotificationVisibleToasts,
	}
}

func (s *Service) PasswordPolicy(ctx context.Context) map[string]interface{} {
	settings := s.loadSecuritySettings(ctx)
	return map[string]interface{}{
		"password_min_length":        settings.PasswordMinLength,
		"password_require_uppercase": settings.PasswordRequireUppercase,
		"password_require_lowercase": settings.PasswordRequireLowercase,
		"password_require_digits":    settings.PasswordRequireDigits,
		"password_require_special":   settings.PasswordRequireSpecial,
	}
}

func (s *Service) SecurityPolicy(ctx context.Context) password.Policy {
	settings := s.loadSecuritySettings(ctx)
	return password.Policy{
		MinLength:        settings.PasswordMinLength,
		RequireUppercase: settings.PasswordRequireUppercase,
		RequireLowercase: settings.PasswordRequireLowercase,
		RequireDigits:    settings.PasswordRequireDigits,
		RequireSpecial:   settings.PasswordRequireSpecial,
	}
}

func (s *Service) UserInfo(user *database.User) map[string]interface{} {
	return map[string]interface{}{
		"id":           user.ID,
		"username":     user.Username,
		"nickname":     user.Nickname,
		"avatar":       user.Avatar,
		"email":        user.Email,
		"phone":        user.Phone,
		"is_active":    user.IsActive,
		"is_superuser": user.IsSuperuser,
		"last_login":   formatTime(user.LastLogin),
		"created_at":   user.CreatedAt.Format("2006-01-02 15:04:05"),
		"updated_at":   user.UpdatedAt.Format("2006-01-02 15:04:05"),
	}
}

func (s *Service) UserMenu(ctx context.Context, user *database.User) ([]menuItem, error) {
	if user.IsSuperuser {
		return cloneMenu(fullMenuTree), nil
	}

	allowedPaths, err := s.listMenuPathsForUser(ctx, user.ID)
	if err != nil {
		return nil, err
	}
	if len(allowedPaths) == 0 {
		allowedPaths = []string{"/dashboard"}
	}
	allowed := make(map[string]struct{}, len(allowedPaths))
	for _, path := range allowedPaths {
		allowed[path] = struct{}{}
	}
	return filterMenu(fullMenuTree, allowed), nil
}

func (s *Service) UserAPI(ctx context.Context, user *database.User) ([]string, error) {
	if user.IsSuperuser {
		return s.listAllAPIKeys(ctx)
	}

	apiIDs, err := s.listAPIIDsForUser(ctx, user.ID)
	if err != nil {
		return nil, err
	}
	return s.listAPIKeysByIDs(ctx, apiIDs)
}

func (s *Service) Overview(ctx context.Context) (map[string]interface{}, error) {
	var userTotal int64
	if err := s.db.WithContext(ctx).Model(&database.User{}).Count(&userTotal).Error; err != nil {
		return nil, err
	}
	var activeUserTotal int64
	if err := s.db.WithContext(ctx).Model(&database.User{}).Where("is_active = ?", true).Count(&activeUserTotal).Error; err != nil {
		return nil, err
	}
	var roleTotal int64
	if err := s.db.WithContext(ctx).Model(&database.Role{}).Count(&roleTotal).Error; err != nil {
		return nil, err
	}
	var apiTotal int64
	if err := s.db.WithContext(ctx).Model(&database.APIRecord{}).Count(&apiTotal).Error; err != nil {
		return nil, err
	}

	todayStart := time.Date(time.Now().Year(), time.Now().Month(), time.Now().Day(), 0, 0, 0, 0, time.Local)
	todayEnd := todayStart.Add(24 * time.Hour)
	var todayAuditTotal int64
	if err := s.db.WithContext(ctx).
		Model(&database.AuditLog{}).
		Where("created_at >= ? AND created_at < ? AND is_deleted = ?", todayStart, todayEnd, false).
		Count(&todayAuditTotal).Error; err != nil {
		return nil, err
	}

	var recentLogs []database.AuditLog
	if err := s.db.WithContext(ctx).
		Where("is_deleted = ?", false).
		Order("created_at DESC, id DESC").
		Limit(8).
		Find(&recentLogs).Error; err != nil {
		return nil, err
	}

	trendStart := todayStart.AddDate(0, 0, -6)
	var trendRows []trendRow
	if err := s.db.WithContext(ctx).
		Table("audit_log").
		Select("DATE(created_at) AS date, COUNT(*) AS count").
		Where("created_at >= ? AND created_at < ? AND is_deleted = ?", trendStart, todayEnd, false).
		Group("DATE(created_at)").
		Order("DATE(created_at) ASC").
		Scan(&trendRows).Error; err != nil {
		return nil, err
	}

	var chartRows []chartRow
	if err := s.db.WithContext(ctx).
		Table("audit_log").
		Select("module, status").
		Where("created_at >= ? AND created_at < ? AND is_deleted = ?", trendStart, todayEnd, false).
		Scan(&chartRows).Error; err != nil {
		return nil, err
	}

	trendByDate := make(map[string]int, len(trendRows))
	for _, row := range trendRows {
		trendByDate[row.Date] = row.Count
	}
	auditTrend := make([]map[string]interface{}, 0, 7)
	for i := 0; i < 7; i++ {
		day := trendStart.AddDate(0, 0, i)
		dateKey := day.Format("2006-01-02")
		auditTrend = append(auditTrend, map[string]interface{}{
			"date":  dateKey,
			"count": trendByDate[dateKey],
		})
	}

	moduleCounts := map[string]int{}
	statusCounts := map[string]int{}
	for _, row := range chartRows {
		module := strings.TrimSpace(row.Module)
		if module == "" {
			module = "基础模块"
		}
		moduleCounts[module]++
		statusCounts[statusBucket(row.Status)]++
	}

	recentActivities := make([]map[string]interface{}, 0, len(recentLogs))
	for _, log := range recentLogs {
		action := log.Summary
		if strings.TrimSpace(action) == "" {
			action = strings.TrimSpace(log.Method + " " + log.Path)
		}
		recentActivities = append(recentActivities, map[string]interface{}{
			"id":            log.ID,
			"username":      fallbackString(log.Username, "system"),
			"module":        fallbackString(log.Module, "基础模块"),
			"action":        action,
			"path":          log.Path,
			"method":        log.Method,
			"status":        log.Status,
			"log_level":     log.LogLevel,
			"response_time": log.ResponseTime,
			"created_at":    log.CreatedAt.Format("2006-01-02 15:04:05"),
		})
	}

	appSettings := s.loadApplicationSettings(ctx)
	return map[string]interface{}{
		"summary": map[string]interface{}{
			"user_total":        userTotal,
			"active_user_total": activeUserTotal,
			"role_total":        roleTotal,
			"api_total":         apiTotal,
			"today_audit_total": todayAuditTotal,
		},
		"system": map[string]interface{}{
			"app_title":                    appSettings.AppTitle,
			"version":                      s.cfg.Version,
			"environment":                  s.cfg.AppEnv,
			"database":                     s.cfg.DBConnection,
			"access_log_enabled":           true,
			"startup_side_effects_enabled": !s.cfg.DisableAutoMigrate,
			"migration_mode":               "startup-auto",
			"seed_mode":                    "startup-auto",
			"api_catalog_mode":             "startup-auto",
			"management_entry":             "go run ./app",
		},
		"audit_trend": auditTrend,
		"charts": map[string]interface{}{
			"module_activity":     buildShareRows(moduleCounts),
			"status_distribution": buildStatusRows(statusCounts),
		},
		"recent_activities": recentActivities,
	}, nil
}

func (s *Service) UpdatePassword(ctx context.Context, user *database.User, req updatePasswordRequest) error {
	if !password.Verify(req.OldPassword, user.Password) {
		return fmt.Errorf("旧密码验证错误")
	}
	if password.Verify(req.NewPassword, user.Password) {
		return fmt.Errorf("新密码不能与当前密码相同")
	}
	policy := s.SecurityPolicy(ctx)
	if err := policy.Validate(req.NewPassword); err != nil {
		return fmt.Errorf("密码强度不足: %w", err)
	}

	hashed, err := password.Hash(req.NewPassword)
	if err != nil {
		return err
	}

	return s.db.WithContext(ctx).Model(user).Updates(map[string]interface{}{
		"password":          hashed,
		"session_version":   user.SessionVersion + 1,
		"refresh_token_jti": nil,
		"updated_at":        time.Now(),
	}).Error
}

func (s *Service) UpdateProfile(ctx context.Context, user *database.User, req updateProfileRequest) error {
	updates := map[string]interface{}{
		"updated_at": time.Now(),
	}

	if req.Nickname != nil {
		updates["nickname"] = nilIfEmpty(*req.Nickname)
	}
	if req.Avatar != nil {
		updates["avatar"] = nilIfEmpty(*req.Avatar)
	}
	if req.Phone != nil {
		updates["phone"] = nilIfEmpty(*req.Phone)
	}
	if req.Email != nil {
		if email := strings.TrimSpace(*req.Email); email != "" {
			var count int64
			if err := s.db.WithContext(ctx).Model(&database.User{}).
				Where("email = ? AND id <> ?", email, user.ID).
				Count(&count).Error; err != nil {
				return err
			}
			if count > 0 {
				return fmt.Errorf("该邮箱地址已被使用")
			}
			updates["email"] = email
		} else {
			updates["email"] = nil
		}
	}

	return s.db.WithContext(ctx).Model(user).Updates(updates).Error
}

func (s *Service) Logout(ctx context.Context, user *database.User) error {
	return s.db.WithContext(ctx).Model(user).Updates(map[string]interface{}{
		"session_version":   user.SessionVersion + 1,
		"refresh_token_jti": nil,
		"updated_at":        time.Now(),
	}).Error
}

func (s *Service) findUser(ctx context.Context, userID int64) (*database.User, error) {
	var user database.User
	if err := s.db.WithContext(ctx).Where("id = ?", userID).First(&user).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, fmt.Errorf("用户不存在")
		}
		return nil, err
	}
	return &user, nil
}

func (h *Handler) Login(w http.ResponseWriter, r *http.Request) {
	var req credentialsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}

	publicPayload, refreshToken, err := h.service.Login(r.Context(), req)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}

	setRefreshTokenCookie(w, refreshToken, h.service.cfg)
	response.Success(w, publicPayload, "成功", nil)
}

func (h *Handler) Refresh(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie(h.service.cfg.RefreshTokenCookieName)
	if err != nil {
		response.Error(w, http.StatusUnauthorized, "缺少刷新令牌", nil)
		return
	}

	publicPayload, refreshToken, err := h.service.Refresh(r.Context(), cookie.Value)
	if err != nil {
		response.Error(w, http.StatusUnauthorized, err.Error(), nil)
		return
	}

	setRefreshTokenCookie(w, refreshToken, h.service.cfg)
	response.Success(w, publicPayload, "成功", nil)
}

func (h *Handler) AppMeta(w http.ResponseWriter, r *http.Request) {
	response.Success(w, h.service.AppMeta(r.Context()), "成功", nil)
}

func (h *Handler) UserInfo(w http.ResponseWriter, r *http.Request) {
	user, ok := currentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	response.Success(w, h.service.UserInfo(user), "成功", nil)
}

func (h *Handler) PasswordPolicy(w http.ResponseWriter, r *http.Request) {
	if _, ok := currentUserFromContext(r.Context()); !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	response.Success(w, h.service.PasswordPolicy(r.Context()), "成功", nil)
}

func (h *Handler) UpdatePassword(w http.ResponseWriter, r *http.Request) {
	user, ok := currentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}

	var req updatePasswordRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	if err := h.service.UpdatePassword(r.Context(), user, req); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}

	response.Success(w, nil, "修改成功", nil)
}

func (h *Handler) UpdateProfile(w http.ResponseWriter, r *http.Request) {
	user, ok := currentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}

	var req updateProfileRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	if err := h.service.UpdateProfile(r.Context(), user, req); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}

	response.Success(w, nil, "个人信息更新成功", nil)
}

func (h *Handler) Logout(w http.ResponseWriter, r *http.Request) {
	user, ok := currentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	if err := h.service.Logout(r.Context(), user); err != nil {
		response.Error(w, http.StatusInternalServerError, "注销失败", nil)
		return
	}

	clearRefreshTokenCookie(w, h.service.cfg.RefreshTokenCookieName)
	response.Success(w, nil, "注销成功", nil)
}

func (h *Handler) NotImplemented(w http.ResponseWriter, r *http.Request) {
	response.NotImplemented(w, "")
}

func (h *Handler) UserMenu(w http.ResponseWriter, r *http.Request) {
	user, ok := currentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	payload, err := h.service.UserMenu(r.Context(), user)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "加载用户菜单失败", nil)
		return
	}
	response.Success(w, payload, "成功", nil)
}

func (h *Handler) UserAPI(w http.ResponseWriter, r *http.Request) {
	user, ok := currentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	payload, err := h.service.UserAPI(r.Context(), user)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "加载用户API权限失败", nil)
		return
	}
	response.Success(w, payload, "成功", nil)
}

func (h *Handler) Overview(w http.ResponseWriter, r *http.Request) {
	if _, ok := currentUserFromContext(r.Context()); !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	payload, err := h.service.Overview(r.Context())
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "加载概览失败", nil)
		return
	}
	response.Success(w, payload, "成功", nil)
}

func (h *Handler) AuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user, err := h.service.Authenticate(r.Context(), r.Header.Get("Authorization"))
		if err != nil {
			response.Error(w, http.StatusUnauthorized, err.Error(), nil)
			return
		}
		next.ServeHTTP(w, r.WithContext(withCurrentUser(r.Context(), user)))
	})
}

func (h *Handler) PermissionMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user, ok := currentUserFromContext(r.Context())
		if !ok {
			response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
			return
		}
		if err := h.service.EnsurePermission(r.Context(), user, r.Method, r.URL.Path); err != nil {
			response.Error(w, http.StatusForbidden, err.Error(), nil)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func withCurrentUser(ctx context.Context, user *database.User) context.Context {
	return context.WithValue(ctx, currentUserKey{}, user)
}

func currentUserFromContext(ctx context.Context) (*database.User, bool) {
	user, ok := ctx.Value(currentUserKey{}).(*database.User)
	return user, ok
}

func setRefreshTokenCookie(w http.ResponseWriter, token string, cfg *config.Config) {
	http.SetCookie(w, &http.Cookie{
		Name:     cfg.RefreshTokenCookieName,
		Value:    token,
		HttpOnly: true,
		Secure:   cfg.RefreshTokenCookieSecure,
		SameSite: sameSiteMode(cfg.RefreshTokenCookieSameSite),
		Path:     "/api",
		MaxAge:   cfg.JWTRefreshTokenExpireDays * 24 * 60 * 60,
	})
}

func clearRefreshTokenCookie(w http.ResponseWriter, cookieName string) {
	http.SetCookie(w, &http.Cookie{
		Name:     cookieName,
		Value:    "",
		HttpOnly: true,
		Path:     "/api",
		MaxAge:   -1,
		Expires:  time.Unix(0, 0),
	})
}

func extractBearerToken(header string) (string, error) {
	const prefix = "Bearer "
	if !strings.HasPrefix(header, prefix) {
		return "", fmt.Errorf("缺少访问令牌")
	}
	return strings.TrimSpace(strings.TrimPrefix(header, prefix)), nil
}

func sameSiteMode(value string) http.SameSite {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "strict":
		return http.SameSiteStrictMode
	case "none":
		return http.SameSiteNoneMode
	default:
		return http.SameSiteLaxMode
	}
}

func nilIfEmpty(value string) interface{} {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return strings.TrimSpace(value)
}

func (s *Service) EnsurePermission(ctx context.Context, user *database.User, method string, path string) error {
	if user.IsSuperuser {
		return nil
	}
	keys, err := s.UserAPI(ctx, user)
	if err != nil {
		return err
	}
	required := strings.ToLower(method) + path
	for _, key := range keys {
		if key == required {
			return nil
		}
	}
	return fmt.Errorf("权限不足 - 方法:%s 路径:%s", method, path)
}

func (s *Service) loadApplicationSettings(ctx context.Context) applicationSettings {
	settings := applicationSettings{
		AppTitle:                  s.cfg.AppTitle,
		ProjectName:               s.cfg.ProjectName,
		AppDescription:            s.cfg.AppDescription,
		Debug:                     s.cfg.Debug,
		LoginPageImageURL:         "",
		LoginPageImageMode:        "contain",
		LoginPageImageZoom:        1,
		LoginPageImagePositionX:   50,
		LoginPageImagePositionY:   50,
		NotificationPosition:      s.cfg.NotificationPosition,
		NotificationDuration:      s.cfg.NotificationDuration,
		NotificationVisibleToasts: s.cfg.NotificationVisibleToasts,
	}
	var stored database.SystemSetting
	if err := s.db.WithContext(ctx).Where("key = ?", "application_config").Limit(1).Find(&stored).Error; err == nil && len(stored.Value) > 0 {
		_ = json.Unmarshal(stored.Value, &settings)
	}
	return settings
}

func (s *Service) loadSecuritySettings(ctx context.Context) securitySettings {
	settings := securitySettings{
		PasswordMinLength:        s.cfg.PasswordMinLength,
		PasswordRequireUppercase: s.cfg.PasswordRequireUppercase,
		PasswordRequireLowercase: s.cfg.PasswordRequireLowercase,
		PasswordRequireDigits:    s.cfg.PasswordRequireDigits,
		PasswordRequireSpecial:   s.cfg.PasswordRequireSpecial,
	}
	var stored database.SystemSetting
	if err := s.db.WithContext(ctx).Where("key = ?", "security_config").Limit(1).Find(&stored).Error; err == nil && len(stored.Value) > 0 {
		_ = json.Unmarshal(stored.Value, &settings)
	}
	return settings
}

func (s *Service) listRolesForUser(ctx context.Context, userID int64) ([]database.Role, error) {
	var roles []database.Role
	err := s.db.WithContext(ctx).
		Table("role").
		Joins("JOIN user_role ON user_role.role_id = role.id").
		Where("user_role.user_id = ?", userID).
		Find(&roles).Error
	return roles, err
}

func (s *Service) listMenuPathsForUser(ctx context.Context, userID int64) ([]string, error) {
	roles, err := s.listRolesForUser(ctx, userID)
	if err != nil {
		return nil, err
	}
	seen := make(map[string]struct{})
	result := make([]string, 0, 8)
	for _, role := range roles {
		for _, path := range role.MenuPaths {
			if _, ok := seen[path]; ok {
				continue
			}
			seen[path] = struct{}{}
			result = append(result, path)
		}
	}
	sort.Strings(result)
	return result, nil
}

func (s *Service) listAPIIDsForUser(ctx context.Context, userID int64) ([]int64, error) {
	roles, err := s.listRolesForUser(ctx, userID)
	if err != nil {
		return nil, err
	}
	seen := make(map[int64]struct{})
	result := make([]int64, 0, 8)
	for _, role := range roles {
		for _, apiID := range role.APIIDs {
			if _, ok := seen[apiID]; ok {
				continue
			}
			seen[apiID] = struct{}{}
			result = append(result, apiID)
		}
	}
	sort.Slice(result, func(i, j int) bool { return result[i] < result[j] })
	return result, nil
}

func (s *Service) listAllAPIKeys(ctx context.Context) ([]string, error) {
	var apis []database.APIRecord
	if err := s.db.WithContext(ctx).Order("id ASC").Find(&apis).Error; err != nil {
		return nil, err
	}
	result := make([]string, 0, len(apis))
	for _, api := range apis {
		result = append(result, strings.ToLower(api.Method)+api.Path)
	}
	return result, nil
}

func (s *Service) listAPIKeysByIDs(ctx context.Context, apiIDs []int64) ([]string, error) {
	if len(apiIDs) == 0 {
		return []string{}, nil
	}
	var apis []database.APIRecord
	if err := s.db.WithContext(ctx).Where("id IN ?", apiIDs).Order("id ASC").Find(&apis).Error; err != nil {
		return nil, err
	}
	result := make([]string, 0, len(apis))
	for _, api := range apis {
		result = append(result, strings.ToLower(api.Method)+api.Path)
	}
	return result, nil
}

func buildShareRows(counts map[string]int) []map[string]interface{} {
	total := 0
	for _, count := range counts {
		total += count
	}
	rows := make([]map[string]interface{}, 0, len(counts))
	for label, count := range counts {
		rows = append(rows, map[string]interface{}{
			"key":   label,
			"label": label,
			"count": count,
			"share": share(count, total),
		})
	}
	sort.Slice(rows, func(i, j int) bool {
		return rows[i]["label"].(string) < rows[j]["label"].(string)
	})
	return rows
}

func buildStatusRows(counts map[string]int) []map[string]interface{} {
	total := 0
	for _, count := range counts {
		total += count
	}
	order := []struct {
		Key   string
		Label string
	}{
		{Key: "2xx", Label: "2xx 成功"},
		{Key: "3xx", Label: "3xx 重定向"},
		{Key: "4xx", Label: "4xx 请求异常"},
		{Key: "5xx", Label: "5xx 服务异常"},
		{Key: "other", Label: "其他状态"},
	}
	rows := make([]map[string]interface{}, 0, len(order))
	for _, item := range order {
		count := counts[item.Key]
		if count == 0 {
			continue
		}
		rows = append(rows, map[string]interface{}{
			"key":   item.Key,
			"label": item.Label,
			"count": count,
			"share": share(count, total),
		})
	}
	return rows
}

func share(count int, total int) int {
	if total <= 0 {
		return 0
	}
	return int(float64(count)/float64(total)*100 + 0.5)
}

func statusBucket(status int) string {
	switch {
	case status >= 200 && status < 300:
		return "2xx"
	case status >= 300 && status < 400:
		return "3xx"
	case status >= 400 && status < 500:
		return "4xx"
	case status >= 500 && status < 600:
		return "5xx"
	default:
		return "other"
	}
}

func fallbackString(value string, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}

func formatTime(value *time.Time) interface{} {
	if value == nil {
		return nil
	}
	return value.Format("2006-01-02 15:04:05")
}

func randomID() string {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return "fallback-refresh-token-id"
	}
	return hex.EncodeToString(buf)
}
