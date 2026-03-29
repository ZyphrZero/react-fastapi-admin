package apis

import (
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"strings"
	"time"

	"gorm.io/gorm"

	"react-go-admin/app/internal/platform/database"
	"react-go-admin/app/internal/platform/response"
)

type Service struct {
	db *gorm.DB
}

type Handler struct {
	service *Service
}

type updateAPIRequest struct {
	ID      int64  `json:"id"`
	Path    string `json:"path"`
	Method  string `json:"method"`
	Summary string `json:"summary"`
	Tags    string `json:"tags"`
}

func NewService(db *gorm.DB) *Service {
	return &Service{db: db}
}

func NewHandler(service *Service) *Handler {
	return &Handler{service: service}
}

func (s *Service) List(page int, pageSize int, path string, summary string, tags string) ([]map[string]interface{}, int64, error) {
	page, pageSize = normalizePage(page, pageSize)
	query := s.db.Model(&database.APIRecord{})
	if trimmed := strings.TrimSpace(path); trimmed != "" {
		query = query.Where("path LIKE ?", "%"+trimmed+"%")
	}
	if trimmed := strings.TrimSpace(summary); trimmed != "" {
		query = query.Where("summary LIKE ?", "%"+trimmed+"%")
	}
	if trimmed := strings.TrimSpace(tags); trimmed != "" {
		values := splitCSV(trimmed)
		if len(values) > 0 {
			sub := s.db
			for i, tag := range values {
				if i == 0 {
					query = query.Where("tags LIKE ?", "%"+tag+"%")
					continue
				}
				query = query.Or("tags LIKE ?", "%"+tag+"%")
			}
			_ = sub
		}
	}
	var total int64
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}
	var items []database.APIRecord
	if err := query.Order("tags ASC, id ASC").Offset((page - 1) * pageSize).Limit(pageSize).Find(&items).Error; err != nil {
		return nil, 0, err
	}
	result := make([]map[string]interface{}, 0, len(items))
	for _, item := range items {
		result = append(result, serializeAPI(item))
	}
	return result, total, nil
}

func (s *Service) Get(apiID int64) (map[string]interface{}, error) {
	var item database.APIRecord
	if err := s.db.Where("id = ?", apiID).First(&item).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, fmt.Errorf("API不存在")
		}
		return nil, err
	}
	return serializeAPI(item), nil
}

func (s *Service) Update(req updateAPIRequest) error {
	var item database.APIRecord
	if err := s.db.Where("id = ?", req.ID).First(&item).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return fmt.Errorf("API不存在")
		}
		return err
	}
	return s.db.Model(&item).Updates(map[string]interface{}{
		"summary":    strings.TrimSpace(req.Summary),
		"tags":       strings.TrimSpace(req.Tags),
		"updated_at": time.Now(),
	}).Error
}

func (s *Service) Delete(apiID int64) error {
	var item database.APIRecord
	if err := s.db.Where("id = ?", apiID).First(&item).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return fmt.Errorf("API不存在")
		}
		return err
	}
	return s.db.Delete(&database.APIRecord{}, apiID).Error
}

func (s *Service) Refresh() error {
	definitions := staticRouteDefinitions()
	return s.db.Transaction(func(tx *gorm.DB) error {
		var existing []database.APIRecord
		if err := tx.Find(&existing).Error; err != nil {
			return err
		}
		existingByKey := make(map[string]database.APIRecord, len(existing))
		stale := make(map[int64]struct{}, len(existing))
		for _, item := range existing {
			key := strings.ToUpper(item.Method) + " " + item.Path
			existingByKey[key] = item
			stale[item.ID] = struct{}{}
		}
		now := time.Now()
		for _, definition := range definitions {
			key := strings.ToUpper(definition.Method) + " " + definition.Path
			if current, ok := existingByKey[key]; ok {
				delete(stale, current.ID)
				if err := tx.Model(&current).Updates(map[string]interface{}{
					"summary":    definition.Summary,
					"tags":       definition.Tags,
					"updated_at": now,
				}).Error; err != nil {
					return err
				}
				continue
			}
			record := &database.APIRecord{
				Method:    strings.ToUpper(definition.Method),
				Path:      definition.Path,
				Summary:   definition.Summary,
				Tags:      definition.Tags,
				CreatedAt: now,
				UpdatedAt: now,
			}
			if err := tx.Create(record).Error; err != nil {
				return err
			}
		}
		for id := range stale {
			if err := tx.Delete(&database.APIRecord{}, id).Error; err != nil {
				return err
			}
		}
		return nil
	})
}

func (s *Service) Tags() ([]map[string]interface{}, error) {
	var apis []database.APIRecord
	if err := s.db.Order("tags ASC").Find(&apis).Error; err != nil {
		return nil, err
	}
	counts := make(map[string]int)
	for _, api := range apis {
		tag := strings.TrimSpace(api.Tags)
		if tag == "" {
			continue
		}
		counts[tag]++
	}
	keys := make([]string, 0, len(counts))
	for key := range counts {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	result := make([]map[string]interface{}, 0, len(keys))
	for _, key := range keys {
		result = append(result, map[string]interface{}{
			"label": key,
			"value": key,
			"count": counts[key],
		})
	}
	return result, nil
}

func (h *Handler) List(w http.ResponseWriter, r *http.Request) {
	page, pageSize := parsePageParams(r)
	items, total, err := h.service.List(page, pageSize, r.URL.Query().Get("path"), r.URL.Query().Get("summary"), r.URL.Query().Get("tags"))
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取 API 列表失败", nil)
		return
	}
	response.Success(w, items, "成功", map[string]interface{}{
		"total":     total,
		"page":      page,
		"page_size": pageSize,
	})
}

func (h *Handler) Get(w http.ResponseWriter, r *http.Request) {
	apiID, err := parseInt64Query(r, "id")
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	item, svcErr := h.service.Get(apiID)
	if svcErr != nil {
		response.Error(w, http.StatusBadRequest, svcErr.Error(), nil)
		return
	}
	response.Success(w, item, "成功", nil)
}

func (h *Handler) Update(w http.ResponseWriter, r *http.Request) {
	var req updateAPIRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	if err := h.service.Update(req); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, nil, "更新成功", nil)
}

func (h *Handler) Delete(w http.ResponseWriter, r *http.Request) {
	apiID, err := parseInt64Query(r, "api_id")
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	if err := h.service.Delete(apiID); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, nil, "删除成功", nil)
}

func (h *Handler) Refresh(w http.ResponseWriter, r *http.Request) {
	if err := h.service.Refresh(); err != nil {
		response.Error(w, http.StatusInternalServerError, "刷新 API 列表失败", nil)
		return
	}
	response.Success(w, nil, "刷新成功", nil)
}

func (h *Handler) Tags(w http.ResponseWriter, r *http.Request) {
	items, err := h.service.Tags()
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取所有API标签失败", nil)
		return
	}
	response.Success(w, items, "成功", nil)
}

func serializeAPI(item database.APIRecord) map[string]interface{} {
	return map[string]interface{}{
		"id":         item.ID,
		"path":       item.Path,
		"method":     item.Method,
		"summary":    item.Summary,
		"tags":       item.Tags,
		"created_at": item.CreatedAt.Format("2006-01-02 15:04:05"),
		"updated_at": item.UpdatedAt.Format("2006-01-02 15:04:05"),
	}
}

func splitCSV(value string) []string {
	parts := strings.Split(value, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}

func parsePageParams(r *http.Request) (int, int) {
	page := 1
	pageSize := 10
	_, _ = fmt.Sscanf(strings.TrimSpace(r.URL.Query().Get("page")), "%d", &page)
	_, _ = fmt.Sscanf(strings.TrimSpace(r.URL.Query().Get("page_size")), "%d", &pageSize)
	return normalizePage(page, pageSize)
}

func normalizePage(page int, pageSize int) (int, int) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 10
	}
	return page, pageSize
}

func parseInt64Query(r *http.Request, key string) (int64, error) {
	raw := strings.TrimSpace(r.URL.Query().Get(key))
	if raw == "" {
		return 0, fmt.Errorf("缺少参数 %s", key)
	}
	var value int64
	if _, err := fmt.Sscanf(raw, "%d", &value); err != nil {
		return 0, fmt.Errorf("参数 %s 无效", key)
	}
	return value, nil
}
