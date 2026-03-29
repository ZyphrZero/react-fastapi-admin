package systemsettings

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"

	"react-fastapi-admin/go-backend/internal/config"
	"react-fastapi-admin/go-backend/internal/modules/base"
	"react-fastapi-admin/go-backend/internal/platform/database"
	"react-fastapi-admin/go-backend/internal/platform/response"
)

const (
	applicationKey = "application_config"
	loggingKey     = "logging_config"
	securityKey    = "security_config"
	storageKey     = "storage_config"
)

type Service struct {
	cfg *config.Config
	db  *gorm.DB
}

type Handler struct {
	service *Service
}

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
	Environment               string  `json:"environment,omitempty"`
}

type loggingSettings struct {
	LogsRoot                string `json:"logs_root"`
	LogRetentionDays        int    `json:"log_retention_days"`
	LogRotation             string `json:"log_rotation"`
	LogMaxFileSize          string `json:"log_max_file_size"`
	LogEnableAccessLog      bool   `json:"log_enable_access_log"`
	AccessLogRequiresRestart bool  `json:"access_log_requires_restart,omitempty"`
}

type securitySettings struct {
	PasswordMinLength        int      `json:"password_min_length"`
	PasswordRequireUppercase bool     `json:"password_require_uppercase"`
	PasswordRequireLowercase bool     `json:"password_require_lowercase"`
	PasswordRequireDigits    bool     `json:"password_require_digits"`
	PasswordRequireSpecial   bool     `json:"password_require_special"`
	RateLimitEnabled         bool     `json:"rate_limit_enabled"`
	RateLimitMaxRequests     int      `json:"rate_limit_max_requests"`
	RateLimitWindowSeconds   int      `json:"rate_limit_window_seconds"`
	IPWhitelist              string   `json:"ip_whitelist"`
	IPWhitelistItems         []string `json:"ip_whitelist_items,omitempty"`
}

type storageSettings struct {
	Provider         string `json:"provider"`
	LocalUploadDir   string `json:"local_upload_dir"`
	LocalFullURL     string `json:"local_full_url"`
	LocalURLPrefix   string `json:"local_url_prefix,omitempty"`
	OSSAccessKeyID   string `json:"oss_access_key_id"`
	OSSAccessKeySecret string `json:"oss_access_key_secret"`
	OSSBucketName    string `json:"oss_bucket_name"`
	OSSEndpoint      string `json:"oss_endpoint"`
	OSSBucketDomain  string `json:"oss_bucket_domain"`
	OSSUploadDir     string `json:"oss_upload_dir"`
}

func NewService(cfg *config.Config, db *gorm.DB) *Service {
	return &Service{cfg: cfg, db: db}
}

func NewHandler(service *Service) *Handler {
	return &Handler{service: service}
}

func (s *Service) GetApplication(ctx context.Context) (applicationSettings, error) {
	current := s.defaultApplicationSettings()
	return s.loadApplicationSettings(ctx, current)
}

func (s *Service) UpdateApplication(ctx context.Context, payload applicationSettings) (applicationSettings, error) {
	payload.Environment = ""
	if err := s.saveJSON(ctx, applicationKey, payload, "应用配置"); err != nil {
		return applicationSettings{}, err
	}
	return s.GetApplication(ctx)
}

func (s *Service) GetLogging(ctx context.Context) (loggingSettings, error) {
	current := loggingSettings{
		LogsRoot:                 s.cfg.LogsRoot,
		LogRetentionDays:         s.cfg.LogRetentionDays,
		LogRotation:              s.cfg.LogRotation,
		LogMaxFileSize:           s.cfg.LogMaxFileSize,
		LogEnableAccessLog:       s.cfg.LogEnableAccessLog,
		AccessLogRequiresRestart: true,
	}
	return s.loadLoggingSettings(ctx, current)
}

func (s *Service) UpdateLogging(ctx context.Context, payload loggingSettings) (loggingSettings, error) {
	payload.AccessLogRequiresRestart = false
	if err := s.saveJSON(ctx, loggingKey, payload, "日志配置"); err != nil {
		return loggingSettings{}, err
	}
	return s.GetLogging(ctx)
}

func (s *Service) GetSecurity(ctx context.Context) (securitySettings, error) {
	current := securitySettings{
		PasswordMinLength:        s.cfg.PasswordMinLength,
		PasswordRequireUppercase: s.cfg.PasswordRequireUppercase,
		PasswordRequireLowercase: s.cfg.PasswordRequireLowercase,
		PasswordRequireDigits:    s.cfg.PasswordRequireDigits,
		PasswordRequireSpecial:   s.cfg.PasswordRequireSpecial,
		RateLimitEnabled:         true,
		RateLimitMaxRequests:     60,
		RateLimitWindowSeconds:   60,
		IPWhitelist:              "",
	}
	return s.loadSecuritySettings(ctx, current)
}

func (s *Service) UpdateSecurity(ctx context.Context, payload securitySettings) (securitySettings, error) {
	payload.IPWhitelist = strings.Join(normalizeWhitelistItems(payload.IPWhitelist), ",")
	payload.IPWhitelistItems = nil
	if err := s.saveJSON(ctx, securityKey, payload, "安全配置"); err != nil {
		return securitySettings{}, err
	}
	return s.GetSecurity(ctx)
}

func (s *Service) GetStorage(ctx context.Context) (storageSettings, error) {
	current := storageSettings{
		Provider:           "local",
		LocalUploadDir:     "uploads",
		LocalFullURL:       "",
		OSSAccessKeyID:     "",
		OSSAccessKeySecret: "",
		OSSBucketName:      "",
		OSSEndpoint:        "",
		OSSBucketDomain:    "",
		OSSUploadDir:       "uploads",
	}
	return s.loadStorageSettings(ctx, current)
}

func (s *Service) UpdateStorage(ctx context.Context, payload storageSettings) (storageSettings, error) {
	payload.LocalUploadDir = normalizeDir(payload.LocalUploadDir, "uploads")
	payload.OSSUploadDir = normalizeDir(payload.OSSUploadDir, "uploads")
	payload.LocalURLPrefix = ""
	if err := s.saveJSON(ctx, storageKey, payload, "存储配置"); err != nil {
		return storageSettings{}, err
	}
	return s.GetStorage(ctx)
}

func (s *Service) defaultApplicationSettings() applicationSettings {
	return applicationSettings{
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
		Environment:               s.cfg.AppEnv,
	}
}

func (s *Service) loadApplicationSettings(ctx context.Context, current applicationSettings) (applicationSettings, error) {
	if err := s.loadJSON(ctx, applicationKey, &current); err != nil {
		return applicationSettings{}, err
	}
	current.Environment = s.cfg.AppEnv
	return current, nil
}

func (s *Service) loadLoggingSettings(ctx context.Context, current loggingSettings) (loggingSettings, error) {
	if err := s.loadJSON(ctx, loggingKey, &current); err != nil {
		return loggingSettings{}, err
	}
	current.AccessLogRequiresRestart = true
	return current, nil
}

func (s *Service) loadSecuritySettings(ctx context.Context, current securitySettings) (securitySettings, error) {
	if err := s.loadJSON(ctx, securityKey, &current); err != nil {
		return securitySettings{}, err
	}
	current.IPWhitelistItems = normalizeWhitelistItems(current.IPWhitelist)
	return current, nil
}

func (s *Service) loadStorageSettings(ctx context.Context, current storageSettings) (storageSettings, error) {
	if err := s.loadJSON(ctx, storageKey, &current); err != nil {
		return storageSettings{}, err
	}
	current.LocalUploadDir = normalizeDir(current.LocalUploadDir, "uploads")
	current.OSSUploadDir = normalizeDir(current.OSSUploadDir, "uploads")
	current.LocalURLPrefix = "/static/" + strings.Trim(current.LocalUploadDir, "/")
	return current, nil
}

func (s *Service) loadJSON(ctx context.Context, key string, target interface{}) error {
	var setting database.SystemSetting
	if err := s.db.WithContext(ctx).Where("key = ?", key).Limit(1).Find(&setting).Error; err != nil {
		return err
	}
	if len(setting.Value) == 0 {
		return nil
	}
	return json.Unmarshal(setting.Value, target)
}

func (s *Service) saveJSON(ctx context.Context, key string, payload interface{}, description string) error {
	value, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	now := time.Now()
	record := &database.SystemSetting{
		Key:         key,
		Value:       value,
		Description: &description,
		CreatedAt:   now,
		UpdatedAt:   now,
	}
	return s.db.WithContext(ctx).Clauses(clause.OnConflict{
		Columns:   []clause.Column{{Name: "key"}},
		DoUpdates: clause.AssignmentColumns([]string{"value", "description", "updated_at"}),
	}).Create(record).Error
}

func ensureSuperuser(r *http.Request) (*database.User, error) {
	user, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		return nil, fmt.Errorf("未授权访问")
	}
	if !user.IsSuperuser {
		return nil, fmt.Errorf("只有超级管理员才能访问系统设置")
	}
	return user, nil
}

func (h *Handler) GetApplication(w http.ResponseWriter, r *http.Request) {
	if _, err := ensureSuperuser(r); err != nil {
		response.Error(w, http.StatusForbidden, err.Error(), nil)
		return
	}
	data, err := h.service.GetApplication(r.Context())
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取基础设置失败", nil)
		return
	}
	response.Success(w, data, "成功", nil)
}

func (h *Handler) UpdateApplication(w http.ResponseWriter, r *http.Request) {
	if _, err := ensureSuperuser(r); err != nil {
		response.Error(w, http.StatusForbidden, err.Error(), nil)
		return
	}
	var payload applicationSettings
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	data, err := h.service.UpdateApplication(r.Context(), payload)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, data, "基础设置已更新", nil)
}

func (h *Handler) GetLogging(w http.ResponseWriter, r *http.Request) {
	if _, err := ensureSuperuser(r); err != nil {
		response.Error(w, http.StatusForbidden, err.Error(), nil)
		return
	}
	data, err := h.service.GetLogging(r.Context())
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取日志设置失败", nil)
		return
	}
	response.Success(w, data, "成功", nil)
}

func (h *Handler) UpdateLogging(w http.ResponseWriter, r *http.Request) {
	if _, err := ensureSuperuser(r); err != nil {
		response.Error(w, http.StatusForbidden, err.Error(), nil)
		return
	}
	var payload loggingSettings
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	data, err := h.service.UpdateLogging(r.Context(), payload)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, data, "日志设置已更新", nil)
}

func (h *Handler) GetSecurity(w http.ResponseWriter, r *http.Request) {
	if _, err := ensureSuperuser(r); err != nil {
		response.Error(w, http.StatusForbidden, err.Error(), nil)
		return
	}
	data, err := h.service.GetSecurity(r.Context())
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取安全设置失败", nil)
		return
	}
	response.Success(w, data, "成功", nil)
}

func (h *Handler) UpdateSecurity(w http.ResponseWriter, r *http.Request) {
	if _, err := ensureSuperuser(r); err != nil {
		response.Error(w, http.StatusForbidden, err.Error(), nil)
		return
	}
	var payload securitySettings
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	data, err := h.service.UpdateSecurity(r.Context(), payload)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, data, "安全设置已更新", nil)
}

func (h *Handler) GetStorage(w http.ResponseWriter, r *http.Request) {
	if _, err := ensureSuperuser(r); err != nil {
		response.Error(w, http.StatusForbidden, err.Error(), nil)
		return
	}
	data, err := h.service.GetStorage(r.Context())
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取存储设置失败", nil)
		return
	}
	response.Success(w, data, "成功", nil)
}

func (h *Handler) UpdateStorage(w http.ResponseWriter, r *http.Request) {
	if _, err := ensureSuperuser(r); err != nil {
		response.Error(w, http.StatusForbidden, err.Error(), nil)
		return
	}
	var payload storageSettings
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	data, err := h.service.UpdateStorage(r.Context(), payload)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, data, "存储设置已更新", nil)
}

func normalizeWhitelistItems(value string) []string {
	parts := strings.FieldsFunc(strings.ReplaceAll(value, "\r\n", "\n"), func(r rune) bool {
		return r == '\n' || r == ',' || r == ';'
	})
	items := make([]string, 0, len(parts))
	seen := map[string]struct{}{}
	for _, part := range parts {
		item := strings.TrimSpace(part)
		if item == "" {
			continue
		}
		if _, ok := seen[item]; ok {
			continue
		}
		seen[item] = struct{}{}
		items = append(items, item)
	}
	return items
}

func normalizeDir(value string, fallback string) string {
	trimmed := strings.Trim(strings.TrimSpace(value), "/")
	if trimmed == "" {
		return fallback
	}
	return trimmed
}
