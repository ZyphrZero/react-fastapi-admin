package auditlog

import (
	"context"
	"encoding/base64"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"gorm.io/gorm"

	"react-go-admin/app/internal/config"
	"react-go-admin/app/internal/modules/base"
	"react-go-admin/app/internal/platform/database"
	"react-go-admin/app/internal/platform/response"
)

type Service struct {
	cfg *config.Config
	db  *gorm.DB
}

type Handler struct {
	service *Service
}

type cursorPayload struct {
	CreatedAt string `json:"created_at"`
	ID        int64  `json:"id"`
}

type exportRequest struct {
	Username      string `json:"username"`
	Module        string `json:"module"`
	Method        string `json:"method"`
	Summary       string `json:"summary"`
	Status        *int   `json:"status"`
	IPAddress     string `json:"ip_address"`
	OperationType string `json:"operation_type"`
	LogLevel      string `json:"log_level"`
	StartTime     string `json:"start_time"`
	EndTime       string `json:"end_time"`
}

func NewService(cfg *config.Config, db *gorm.DB) *Service {
	return &Service{cfg: cfg, db: db}
}

func NewHandler(service *Service) *Handler {
	return &Handler{service: service}
}

func (s *Service) List(ctx context.Context, pageSize int, cursor string, filters exportRequest) ([]map[string]interface{}, int64, bool, string, error) {
	if pageSize < 1 {
		pageSize = 100
	}
	if pageSize > 200 {
		pageSize = 200
	}

	baseQuery := s.db.WithContext(ctx).Model(&database.AuditLog{}).Where("is_deleted = ?", false)
	baseQuery = applyFilters(baseQuery, filters)

	var total int64
	if err := baseQuery.Count(&total).Error; err != nil {
		return nil, 0, false, "", err
	}

	query := baseQuery
	if cursor != "" {
		createdAt, logID, err := decodeCursor(cursor)
		if err != nil {
			return nil, 0, false, "", fmt.Errorf("无效的分页游标")
		}
		query = query.Where("(created_at < ?) OR (created_at = ? AND id < ?)", createdAt, createdAt, logID)
	}

	var logs []database.AuditLog
	if err := query.Order("created_at DESC, id DESC").Limit(pageSize + 1).Find(&logs).Error; err != nil {
		return nil, 0, false, "", err
	}

	hasMore := len(logs) > pageSize
	if hasMore {
		logs = logs[:pageSize]
	}
	nextCursor := ""
	if hasMore && len(logs) > 0 {
		nextCursor = encodeCursor(logs[len(logs)-1].CreatedAt, logs[len(logs)-1].ID)
	}

	items := make([]map[string]interface{}, 0, len(logs))
	for _, log := range logs {
		items = append(items, serializeListLog(log))
	}
	return items, total, hasMore, nextCursor, nil
}

func (s *Service) Detail(ctx context.Context, logID int64) (map[string]interface{}, error) {
	var log database.AuditLog
	if err := s.db.WithContext(ctx).Where("id = ? AND is_deleted = ?", logID, false).First(&log).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, fmt.Errorf("日志不存在")
		}
		return nil, err
	}
	return serializeDetailLog(log), nil
}

func (s *Service) Delete(ctx context.Context, logID int64) error {
	var log database.AuditLog
	if err := s.db.WithContext(ctx).Where("id = ?", logID).First(&log).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return fmt.Errorf("日志不存在")
		}
		return err
	}
	return s.db.WithContext(ctx).Model(&log).Updates(map[string]interface{}{
		"is_deleted": true,
		"updated_at": time.Now(),
	}).Error
}

func (s *Service) BatchDelete(ctx context.Context, logIDs []int64) (int64, error) {
	if len(logIDs) == 0 {
		return 0, fmt.Errorf("请提供要删除的日志ID")
	}
	result := s.db.WithContext(ctx).Model(&database.AuditLog{}).
		Where("id IN ?", logIDs).
		Updates(map[string]interface{}{"is_deleted": true, "updated_at": time.Now()})
	return result.RowsAffected, result.Error
}

func (s *Service) Clear(ctx context.Context, days *int) (int64, error) {
	query := s.db.WithContext(ctx).Model(&database.AuditLog{}).Where("is_deleted = ?", false)
	if days != nil {
		clearBefore := time.Now().AddDate(0, 0, -*days)
		query = query.Where("created_at < ?", clearBefore)
	}
	result := query.Updates(map[string]interface{}{"is_deleted": true, "updated_at": time.Now()})
	return result.RowsAffected, result.Error
}

func (s *Service) Statistics(ctx context.Context, days int) (map[string]int, error) {
	if days < 1 {
		days = 1
	}
	if days > 30 {
		days = 30
	}
	startDate := time.Now().AddDate(0, 0, -(days - 1))
	startDate = time.Date(startDate.Year(), startDate.Month(), startDate.Day(), 0, 0, 0, 0, startDate.Location())

	type row struct {
		Date  string `gorm:"column:date"`
		Count int    `gorm:"column:count"`
	}
	var rows []row
	if err := s.db.WithContext(ctx).
		Table("audit_log").
		Select("DATE(created_at) AS date, COUNT(*) AS count").
		Where("created_at >= ? AND is_deleted = ?", startDate, false).
		Group("DATE(created_at)").
		Order("DATE(created_at) ASC").
		Scan(&rows).Error; err != nil {
		return nil, err
	}
	result := make(map[string]int, days)
	for i := 0; i < days; i++ {
		dateKey := startDate.AddDate(0, 0, i).Format("2006-01-02")
		result[dateKey] = 0
	}
	for _, row := range rows {
		result[row.Date] = row.Count
	}
	return result, nil
}

func (s *Service) Export(ctx context.Context, filters exportRequest) (string, error) {
	exportDir := filepath.Join(s.cfg.BaseDir, "exports", "auditlogs")
	if err := os.MkdirAll(exportDir, 0o755); err != nil {
		return "", err
	}
	filename := fmt.Sprintf("auditlog_export_%s.csv", time.Now().Format("20060102150405"))
	fullPath := filepath.Join(exportDir, filename)

	query := s.db.WithContext(ctx).Model(&database.AuditLog{}).Where("is_deleted = ?", false)
	query = applyFilters(query, filters)
	var logs []database.AuditLog
	if err := query.Order("created_at DESC").Find(&logs).Error; err != nil {
		return "", err
	}

	file, err := os.Create(fullPath)
	if err != nil {
		return "", err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	headers := []string{"ID", "用户ID", "用户名", "功能模块", "请求描述", "请求方法", "请求路径", "状态码", "响应时间(ms)", "IP地址", "操作类型", "日志级别", "创建时间", "更新时间"}
	if err := writer.Write(headers); err != nil {
		return "", err
	}
	for _, log := range logs {
		row := []string{
			strconv.FormatInt(log.ID, 10),
			strconv.FormatInt(log.UserID, 10),
			log.Username,
			log.Module,
			log.Summary,
			log.Method,
			log.Path,
			strconv.Itoa(log.Status),
			strconv.Itoa(log.ResponseTime),
			log.IPAddress,
			log.OperationType,
			log.LogLevel,
			log.CreatedAt.Format("2006-01-02 15:04:05"),
			log.UpdatedAt.Format("2006-01-02 15:04:05"),
		}
		if err := writer.Write(row); err != nil {
			return "", err
		}
	}
	return filename, nil
}

func (h *Handler) List(w http.ResponseWriter, r *http.Request) {
	pageSize := parseIntQuery(r.URL.Query().Get("page_size"), 100)
	filters, err := parseFiltersFromQuery(r)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	items, total, hasMore, nextCursor, svcErr := h.service.List(r.Context(), pageSize, strings.TrimSpace(r.URL.Query().Get("cursor")), filters)
	if svcErr != nil {
		response.Error(w, http.StatusInternalServerError, "获取审计日志失败", nil)
		return
	}
	response.Success(w, items, "成功", map[string]interface{}{
		"total":       total,
		"page_size":   pageSize,
		"has_more":    hasMore,
		"next_cursor": nextCursor,
	})
}

func (h *Handler) Detail(w http.ResponseWriter, r *http.Request) {
	logID, err := parsePathID(r.URL.Path)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	item, svcErr := h.service.Detail(r.Context(), logID)
	if svcErr != nil {
		response.Error(w, http.StatusBadRequest, svcErr.Error(), nil)
		return
	}
	response.Success(w, item, "成功", nil)
}

func (h *Handler) Delete(w http.ResponseWriter, r *http.Request) {
	user, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	if !user.IsSuperuser {
		response.Error(w, http.StatusForbidden, "权限不足，只有超级管理员可以删除日志", nil)
		return
	}
	logID, err := parsePathID(r.URL.Path)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	if err := h.service.Delete(r.Context(), logID); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, nil, "删除成功", nil)
}

func (h *Handler) BatchDelete(w http.ResponseWriter, r *http.Request) {
	user, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	if !user.IsSuperuser {
		response.Error(w, http.StatusForbidden, "权限不足，只有超级管理员可以删除日志", nil)
		return
	}
	var logIDs []int64
	if err := json.NewDecoder(r.Body).Decode(&logIDs); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	count, err := h.service.BatchDelete(r.Context(), logIDs)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, nil, fmt.Sprintf("成功删除%d条日志", count), nil)
}

func (h *Handler) Clear(w http.ResponseWriter, r *http.Request) {
	user, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	if !user.IsSuperuser {
		response.Error(w, http.StatusForbidden, "权限不足，只有超级管理员可以清空日志", nil)
		return
	}
	var days *int
	if raw := strings.TrimSpace(r.URL.Query().Get("days")); raw != "" {
		value, err := strconv.Atoi(raw)
		if err != nil {
			response.Error(w, http.StatusBadRequest, "days 参数无效", nil)
			return
		}
		days = &value
	}
	count, err := h.service.Clear(r.Context(), days)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "清理日志失败", nil)
		return
	}
	response.Success(w, nil, fmt.Sprintf("成功清除%d条日志", count), nil)
}

func (h *Handler) Export(w http.ResponseWriter, r *http.Request) {
	user, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	_ = user
	var req exportRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	filename, err := h.service.Export(r.Context(), req)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "导出日志失败", nil)
		return
	}
	response.Success(w, nil, fmt.Sprintf("正在导出日志，文件将保存为 %s", filename), nil)
}

func (h *Handler) Download(w http.ResponseWriter, r *http.Request) {
	filename := pathTail(r.URL.Path)
	if strings.Contains(filename, "..") || strings.Contains(filename, "/") || strings.Contains(filename, "\\") || filename == "" {
		response.Error(w, http.StatusBadRequest, "无效的文件名", nil)
		return
	}
	fullPath := filepath.Join(h.service.cfg.BaseDir, "exports", "auditlogs", filename)
	if _, err := os.Stat(fullPath); err != nil {
		response.Error(w, http.StatusNotFound, "文件不存在或已被删除", nil)
		return
	}
	http.ServeFile(w, r, fullPath)
}

func (h *Handler) Statistics(w http.ResponseWriter, r *http.Request) {
	days := parseIntQuery(r.URL.Query().Get("days"), 7)
	stats, err := h.service.Statistics(r.Context(), days)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取统计失败", nil)
		return
	}
	response.Success(w, stats, "成功", nil)
}

func applyFilters(query *gorm.DB, filters exportRequest) *gorm.DB {
	if trimmed := strings.TrimSpace(filters.Username); trimmed != "" {
		query = query.Where("username LIKE ?", "%"+trimmed+"%")
	}
	if trimmed := strings.TrimSpace(filters.Module); trimmed != "" {
		query = query.Where("module LIKE ?", "%"+trimmed+"%")
	}
	if trimmed := strings.TrimSpace(filters.Method); trimmed != "" {
		query = query.Where("method = ?", strings.ToUpper(trimmed))
	}
	if trimmed := strings.TrimSpace(filters.Summary); trimmed != "" {
		query = query.Where("summary LIKE ?", "%"+trimmed+"%")
	}
	if filters.Status != nil {
		query = query.Where("status = ?", *filters.Status)
	}
	if trimmed := strings.TrimSpace(filters.IPAddress); trimmed != "" {
		query = query.Where("ip_address LIKE ?", "%"+trimmed+"%")
	}
	if trimmed := strings.TrimSpace(filters.OperationType); trimmed != "" {
		query = query.Where("operation_type LIKE ?", "%"+trimmed+"%")
	}
	if trimmed := strings.TrimSpace(filters.LogLevel); trimmed != "" {
		query = query.Where("log_level = ?", strings.ToLower(trimmed))
	}
	if startTime, err := parseDateTime(filters.StartTime); err == nil && !startTime.IsZero() {
		query = query.Where("created_at >= ?", startTime)
	}
	if endTime, err := parseDateTime(filters.EndTime); err == nil && !endTime.IsZero() {
		query = query.Where("created_at <= ?", endTime)
	}
	return query
}

func parseFiltersFromQuery(r *http.Request) (exportRequest, error) {
	filters := exportRequest{
		Username:      r.URL.Query().Get("username"),
		Module:        r.URL.Query().Get("module"),
		Method:        r.URL.Query().Get("method"),
		Summary:       r.URL.Query().Get("summary"),
		IPAddress:     r.URL.Query().Get("ip_address"),
		OperationType: r.URL.Query().Get("operation_type"),
		LogLevel:      r.URL.Query().Get("log_level"),
		StartTime:     r.URL.Query().Get("start_time"),
		EndTime:       r.URL.Query().Get("end_time"),
	}
	if raw := strings.TrimSpace(r.URL.Query().Get("status")); raw != "" {
		value, err := strconv.Atoi(raw)
		if err != nil {
			return filters, fmt.Errorf("status 参数无效")
		}
		filters.Status = &value
	}
	return filters, nil
}

func parseDateTime(value string) (time.Time, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return time.Time{}, nil
	}
	layouts := []string{
		"2006-01-02T15:04:05",
		"2006-01-02 15:04:05",
		"2006-01-02T15:04",
	}
	for _, layout := range layouts {
		if parsed, err := time.ParseInLocation(layout, value, time.Local); err == nil {
			return parsed, nil
		}
	}
	return time.Time{}, fmt.Errorf("invalid datetime")
}

func encodeCursor(createdAt time.Time, logID int64) string {
	payload, _ := json.Marshal(cursorPayload{
		CreatedAt: createdAt.Format(time.RFC3339Nano),
		ID:        logID,
	})
	return base64.URLEncoding.EncodeToString(payload)
}

func decodeCursor(cursor string) (time.Time, int64, error) {
	raw, err := base64.URLEncoding.DecodeString(cursor)
	if err != nil {
		return time.Time{}, 0, err
	}
	var payload cursorPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return time.Time{}, 0, err
	}
	createdAt, err := time.Parse(time.RFC3339Nano, payload.CreatedAt)
	if err != nil {
		return time.Time{}, 0, err
	}
	return createdAt, payload.ID, nil
}

func serializeListLog(log database.AuditLog) map[string]interface{} {
	return map[string]interface{}{
		"id":             log.ID,
		"user_id":        log.UserID,
		"username":       log.Username,
		"module":         log.Module,
		"summary":        log.Summary,
		"method":         log.Method,
		"path":           log.Path,
		"status":         log.Status,
		"response_time":  log.ResponseTime,
		"ip_address":     log.IPAddress,
		"operation_type": log.OperationType,
		"log_level":      log.LogLevel,
		"created_at":     log.CreatedAt.Format("2006-01-02 15:04:05"),
	}
}

func serializeDetailLog(log database.AuditLog) map[string]interface{} {
	item := serializeListLog(log)
	item["request_args"] = decodeJSON(log.RequestArgs)
	item["response_body"] = decodeJSON(log.ResponseBody)
	item["user_agent"] = log.UserAgent
	item["updated_at"] = log.UpdatedAt.Format("2006-01-02 15:04:05")
	return item
}

func decodeJSON(value []byte) interface{} {
	if len(value) == 0 {
		return nil
	}
	var decoded interface{}
	if err := json.Unmarshal(value, &decoded); err != nil {
		return string(value)
	}
	return decoded
}

func parseIntQuery(raw string, fallback int) int {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return fallback
	}
	value, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}
	return value
}

func parsePathID(path string) (int64, error) {
	raw := pathTail(path)
	value, err := strconv.ParseInt(raw, 10, 64)
	if err != nil {
		return 0, fmt.Errorf("日志ID无效")
	}
	return value, nil
}

func pathTail(path string) string {
	parts := strings.Split(strings.Trim(strings.TrimSpace(path), "/"), "/")
	if len(parts) == 0 {
		return ""
	}
	return parts[len(parts)-1]
}
