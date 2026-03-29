package roles

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"strings"
	"time"

	"gorm.io/gorm"

	"react-go-admin/app/internal/modules/base"
	"react-go-admin/app/internal/platform/database"
	"react-go-admin/app/internal/platform/response"
)

type Service struct {
	db    *gorm.DB
	authz *base.Service
}

type Handler struct {
	service *Service
}

type createRoleRequest struct {
	Name      string   `json:"name"`
	Desc      string   `json:"desc"`
	MenuPaths []string `json:"menu_paths"`
	APIIDs    []int64  `json:"api_ids"`
}

type updateRoleRequest struct {
	ID        int64     `json:"id"`
	Name      *string   `json:"name"`
	Desc      *string   `json:"desc"`
	MenuPaths *[]string `json:"menu_paths"`
	APIIDs    *[]int64  `json:"api_ids"`
}

func NewService(db *gorm.DB, authz *base.Service) *Service {
	return &Service{db: db, authz: authz}
}

func NewHandler(service *Service) *Handler {
	return &Handler{service: service}
}

func (s *Service) List(page int, pageSize int, roleName string) ([]map[string]interface{}, int64, error) {
	page, pageSize = normalizePage(page, pageSize)
	query := s.db.Model(&database.Role{})
	if trimmed := strings.TrimSpace(roleName); trimmed != "" {
		query = query.Where("name LIKE ?", "%"+trimmed+"%")
	}
	var total int64
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}
	var roles []database.Role
	if err := query.Order("id ASC").Offset((page - 1) * pageSize).Limit(pageSize).Find(&roles).Error; err != nil {
		return nil, 0, err
	}
	counts, err := s.userCountsByRoleID(roleIDs(roles))
	if err != nil {
		return nil, 0, err
	}
	items := make([]map[string]interface{}, 0, len(roles))
	for _, role := range roles {
		items = append(items, map[string]interface{}{
			"id":         role.ID,
			"name":       role.Name,
			"desc":       stringPtr(role.Desc),
			"menu_paths": []string(role.MenuPaths),
			"api_ids":    []int64(role.APIIDs),
			"menu_count": len(role.MenuPaths),
			"api_count":  len(role.APIIDs),
			"user_count": counts[role.ID],
			"created_at": role.CreatedAt.Format("2006-01-02 15:04:05"),
			"updated_at": role.UpdatedAt.Format("2006-01-02 15:04:05"),
		})
	}
	return items, total, nil
}

func (s *Service) Get(roleID int64) (map[string]interface{}, error) {
	var role database.Role
	if err := s.db.Where("id = ?", roleID).First(&role).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, fmt.Errorf("角色不存在")
		}
		return nil, err
	}
	menuPaths := append([]string(nil), role.MenuPaths...)
	apiIDs := append([]int64(nil), role.APIIDs...)
	sort.Strings(menuPaths)
	sort.Slice(apiIDs, func(i, j int) bool { return apiIDs[i] < apiIDs[j] })
	return map[string]interface{}{
		"id":         role.ID,
		"name":       role.Name,
		"desc":       stringPtr(role.Desc),
		"menu_paths": menuPaths,
		"api_ids":    apiIDs,
		"menu_count": len(menuPaths),
		"api_count":  len(apiIDs),
		"created_at": role.CreatedAt.Format("2006-01-02 15:04:05"),
		"updated_at": role.UpdatedAt.Format("2006-01-02 15:04:05"),
	}, nil
}

func (s *Service) PermissionOptions() (map[string]interface{}, error) {
	var apis []database.APIRecord
	if err := s.db.Order("tags ASC, path ASC, method ASC").Find(&apis).Error; err != nil {
		return nil, err
	}
	groupMap := make(map[string][]map[string]interface{})
	for _, api := range apis {
		tag := strings.TrimSpace(api.Tags)
		if tag == "" {
			tag = "未分类"
		}
		groupMap[tag] = append(groupMap[tag], map[string]interface{}{
			"id":         api.ID,
			"path":       api.Path,
			"method":     api.Method,
			"summary":    api.Summary,
			"tags":       tag,
			"created_at": api.CreatedAt.Format("2006-01-02 15:04:05"),
			"updated_at": api.UpdatedAt.Format("2006-01-02 15:04:05"),
		})
	}
	tags := make([]string, 0, len(groupMap))
	for tag := range groupMap {
		tags = append(tags, tag)
	}
	sort.Strings(tags)
	apiGroups := make([]map[string]interface{}, 0, len(tags))
	for _, tag := range tags {
		apiGroups = append(apiGroups, map[string]interface{}{
			"tag":   tag,
			"items": groupMap[tag],
		})
	}
	return map[string]interface{}{
		"menu_tree":  base.AssignableMenuTree(),
		"api_groups": apiGroups,
	}, nil
}

func (s *Service) Create(ctx context.Context, actor *database.User, req createRoleRequest) error {
	name := strings.TrimSpace(req.Name)
	if name == "" {
		return fmt.Errorf("该角色名称已存在")
	}
	var count int64
	if err := s.db.Model(&database.Role{}).Where("name = ?", name).Count(&count).Error; err != nil {
		return err
	}
	if count > 0 {
		return fmt.Errorf("该角色名称已存在")
	}
	menuPaths, apiIDs, err := s.normalizePermissions(req.MenuPaths, req.APIIDs)
	if err != nil {
		return err
	}
	if err := s.authz.EnsureCanCreateRole(ctx, actor, menuPaths, apiIDs); err != nil {
		return err
	}
	role := &database.Role{
		Name:      name,
		Desc:      normalizeNullableString(req.Desc),
		MenuPaths: database.JSONStringSlice(menuPaths),
		APIIDs:    database.JSONInt64Slice(apiIDs),
	}
	return s.db.Create(role).Error
}

func (s *Service) Update(ctx context.Context, actor *database.User, req updateRoleRequest) error {
	var role database.Role
	if err := s.db.Where("id = ?", req.ID).First(&role).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return fmt.Errorf("角色不存在")
		}
		return err
	}
	updates := map[string]interface{}{
		"updated_at": time.Now(),
	}
	if req.Name != nil {
		name := strings.TrimSpace(*req.Name)
		var count int64
		if err := s.db.Model(&database.Role{}).Where("name = ? AND id <> ?", name, role.ID).Count(&count).Error; err != nil {
			return err
		}
		if count > 0 {
			return fmt.Errorf("该角色名称已存在")
		}
		updates["name"] = name
	}
	if req.Desc != nil {
		updates["desc"] = normalizeNullableString(*req.Desc)
	}
	if req.MenuPaths != nil || req.APIIDs != nil {
		nextMenuPaths := []string(role.MenuPaths)
		nextAPIIDs := []int64(role.APIIDs)
		if req.MenuPaths != nil {
			nextMenuPaths = append([]string(nil), (*req.MenuPaths)...)
		}
		if req.APIIDs != nil {
			nextAPIIDs = append([]int64(nil), (*req.APIIDs)...)
		}
		menuPaths, apiIDs, err := s.normalizePermissions(nextMenuPaths, nextAPIIDs)
		if err != nil {
			return err
		}
		if err := s.authz.EnsureCanUpdateRole(ctx, actor, &role, menuPaths, apiIDs); err != nil {
			return err
		}
		updates["menu_paths"] = database.JSONStringSlice(menuPaths)
		updates["api_ids"] = database.JSONInt64Slice(apiIDs)
	} else {
		if err := s.authz.EnsureCanManageRole(ctx, actor, &role, "修改"); err != nil {
			return err
		}
	}
	return s.db.Model(&role).Updates(updates).Error
}

func (s *Service) Delete(ctx context.Context, actor *database.User, roleID int64) error {
	var role database.Role
	if err := s.db.Where("id = ?", roleID).First(&role).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return fmt.Errorf("角色不存在")
		}
		return err
	}
	if err := s.authz.EnsureCanManageRole(ctx, actor, &role, "删除"); err != nil {
		return err
	}
	return s.db.Delete(&database.Role{}, roleID).Error
}

func (h *Handler) List(w http.ResponseWriter, r *http.Request) {
	page, pageSize := parsePageParams(r)
	items, total, err := h.service.List(page, pageSize, r.URL.Query().Get("role_name"))
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取角色列表失败", nil)
		return
	}
	response.Success(w, items, "成功", map[string]interface{}{
		"total":     total,
		"page":      page,
		"page_size": pageSize,
	})
}

func (h *Handler) Get(w http.ResponseWriter, r *http.Request) {
	roleID, err := parseInt64Query(r, "role_id")
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	item, svcErr := h.service.Get(roleID)
	if svcErr != nil {
		response.Error(w, http.StatusBadRequest, svcErr.Error(), nil)
		return
	}
	response.Success(w, item, "成功", nil)
}

func (h *Handler) PermissionOptions(w http.ResponseWriter, r *http.Request) {
	options, err := h.service.PermissionOptions()
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取角色权限选项失败", nil)
		return
	}
	response.Success(w, options, "成功", nil)
}

func (h *Handler) Create(w http.ResponseWriter, r *http.Request) {
	actor, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	var req createRoleRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	if err := h.service.Create(r.Context(), actor, req); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, nil, "创建成功", nil)
}

func (h *Handler) Update(w http.ResponseWriter, r *http.Request) {
	actor, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	var req updateRoleRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	if err := h.service.Update(r.Context(), actor, req); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, nil, "更新成功", nil)
}

func (h *Handler) Delete(w http.ResponseWriter, r *http.Request) {
	actor, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	roleID, err := parseInt64Query(r, "role_id")
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	if err := h.service.Delete(r.Context(), actor, roleID); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, nil, "删除成功", nil)
}

func (s *Service) userCountsByRoleID(roleIDs []int64) (map[int64]int64, error) {
	result := make(map[int64]int64)
	if len(roleIDs) == 0 {
		return result, nil
	}
	type row struct {
		RoleID int64 `gorm:"column:role_id"`
		Count  int64 `gorm:"column:count"`
	}
	var rows []row
	err := s.db.Table("user_role").
		Select("role_id, COUNT(*) AS count").
		Where("role_id IN ?", roleIDs).
		Group("role_id").
		Scan(&rows).Error
	if err != nil {
		return nil, err
	}
	for _, row := range rows {
		result[row.RoleID] = row.Count
	}
	return result, nil
}

func (s *Service) normalizePermissions(menuPaths []string, apiIDs []int64) ([]string, []int64, error) {
	unknown := base.FindUnknownMenuPaths(menuPaths)
	if len(unknown) > 0 {
		return nil, nil, fmt.Errorf("菜单权限不存在: %s", strings.Join(unknown, ", "))
	}
	normalizedMenuPaths := base.NormalizeMenuPaths(menuPaths)
	sort.Strings(normalizedMenuPaths)

	normalizedAPIIDs := dedupeInt64s(apiIDs)
	if len(normalizedAPIIDs) > 0 {
		var apis []database.APIRecord
		if err := s.db.Where("id IN ?", normalizedAPIIDs).Find(&apis).Error; err != nil {
			return nil, nil, err
		}
		found := make(map[int64]struct{}, len(apis))
		for _, api := range apis {
			found[api.ID] = struct{}{}
		}
		missing := make([]string, 0)
		for _, apiID := range normalizedAPIIDs {
			if _, ok := found[apiID]; !ok {
				missing = append(missing, fmt.Sprintf("%d", apiID))
			}
		}
		if len(missing) > 0 {
			return nil, nil, fmt.Errorf("API权限不存在: %s", strings.Join(missing, ", "))
		}
	}
	return normalizedMenuPaths, normalizedAPIIDs, nil
}

func roleIDs(items []database.Role) []int64 {
	result := make([]int64, 0, len(items))
	for _, item := range items {
		result = append(result, item.ID)
	}
	return result
}

func dedupeInt64s(values []int64) []int64 {
	seen := make(map[int64]struct{})
	result := make([]int64, 0, len(values))
	for _, value := range values {
		if _, ok := seen[value]; ok {
			continue
		}
		seen[value] = struct{}{}
		result = append(result, value)
	}
	sort.Slice(result, func(i, j int) bool { return result[i] < result[j] })
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

func stringPtr(value *string) interface{} {
	if value == nil {
		return nil
	}
	return *value
}

func normalizeNullableString(value string) *string {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return nil
	}
	return &trimmed
}
