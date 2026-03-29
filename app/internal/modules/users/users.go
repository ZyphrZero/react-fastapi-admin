package users

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"gorm.io/gorm"

	"react-go-admin/app/internal/modules/base"
	"react-go-admin/app/internal/platform/database"
	"react-go-admin/app/internal/platform/password"
	"react-go-admin/app/internal/platform/response"
)

type Service struct {
	db    *gorm.DB
	authz *base.Service
}

type Handler struct {
	service *Service
}

type createUserRequest struct {
	Email       string  `json:"email"`
	Username    string  `json:"username"`
	Nickname    *string `json:"nickname"`
	Phone       *string `json:"phone"`
	Password    string  `json:"password"`
	IsActive    *bool   `json:"is_active"`
	IsSuperuser *bool   `json:"is_superuser"`
	RoleIDs     []int64 `json:"role_ids"`
}

type updateUserRequest struct {
	ID          int64   `json:"id"`
	Username    *string `json:"username"`
	Email       *string `json:"email"`
	Nickname    *string `json:"nickname"`
	Phone       *string `json:"phone"`
	Password    *string `json:"password"`
	IsActive    *bool   `json:"is_active"`
	IsSuperuser *bool   `json:"is_superuser"`
	RoleIDs     []int64 `json:"role_ids"`
}

type resetPasswordRequest struct {
	UserID      int64  `json:"user_id"`
	NewPassword string `json:"new_password"`
}

type roleSummary struct {
	ID   int64  `json:"id"`
	Name string `json:"name"`
}

func NewService(db *gorm.DB, authz *base.Service) *Service {
	return &Service{db: db, authz: authz}
}

func NewHandler(service *Service) *Handler {
	return &Handler{service: service}
}

func (s *Service) List(ctx context.Context, page int, pageSize int, username string, nickname string, email string) ([]map[string]interface{}, int64, error) {
	page, pageSize = normalizePage(page, pageSize)

	query := s.db.WithContext(ctx).Model(&database.User{})
	if username != "" {
		query = query.Where("username LIKE ?", "%"+username+"%")
	}
	if nickname != "" {
		query = query.Where("nickname LIKE ?", "%"+nickname+"%")
	}
	if email != "" {
		query = query.Where("email LIKE ?", "%"+email+"%")
	}

	var total int64
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	var users []database.User
	if err := query.Order("id ASC").Offset((page - 1) * pageSize).Limit(pageSize).Find(&users).Error; err != nil {
		return nil, 0, err
	}

	roleMap, err := s.loadRoleSummariesByUserIDs(ctx, userIDs(users))
	if err != nil {
		return nil, 0, err
	}

	items := make([]map[string]interface{}, 0, len(users))
	for _, user := range users {
		items = append(items, serializeUser(user, roleMap[user.ID]))
	}
	return items, total, nil
}

func (s *Service) Get(ctx context.Context, userID int64) (map[string]interface{}, error) {
	var user database.User
	if err := s.db.WithContext(ctx).Where("id = ?", userID).First(&user).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, fmt.Errorf("用户不存在")
		}
		return nil, err
	}
	roleMap, err := s.loadRoleSummariesByUserIDs(ctx, []int64{userID})
	if err != nil {
		return nil, err
	}
	return serializeUser(user, roleMap[userID]), nil
}

func (s *Service) Create(ctx context.Context, actor *database.User, req createUserRequest) error {
	policy := s.authz.SecurityPolicy(ctx)
	if err := policy.Validate(req.Password); err != nil {
		return fmt.Errorf("密码强度不足: %w", err)
	}
	email := normalizeNullableString(req.Email)
	username := strings.TrimSpace(req.Username)
	if username == "" {
		return fmt.Errorf("用户名不能为空")
	}
	if email != nil {
		exists, err := s.emailExists(ctx, *email, 0)
		if err != nil {
			return err
		}
		if exists {
			return fmt.Errorf("该邮箱地址已被使用")
		}
	}
	usernameExists, err := s.usernameExists(ctx, username, 0)
	if err != nil {
		return err
	}
	if usernameExists {
		return fmt.Errorf("该用户名已被使用")
	}

	roleIDs := append([]int64(nil), req.RoleIDs...)
	isSuperuser := req.IsSuperuser != nil && *req.IsSuperuser
	if !isSuperuser && len(roleIDs) == 0 {
		defaultRoleID, err := s.getRoleIDByName(ctx, "普通用户")
		if err != nil {
			return err
		}
		roleIDs = []int64{defaultRoleID}
	}

	if err := s.ensureRolesExist(ctx, roleIDs); err != nil {
		return err
	}
	if err := s.authz.EnsureCanCreateUser(ctx, actor, isSuperuser, roleIDs); err != nil {
		return err
	}

	hashedPassword, err := password.Hash(req.Password)
	if err != nil {
		return err
	}

	isActive := true
	if req.IsActive != nil {
		isActive = *req.IsActive
	}

	return s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		user := &database.User{
			Username:       username,
			Email:          email,
			Nickname:       normalizeStringPtr(req.Nickname),
			Phone:          normalizeStringPtr(req.Phone),
			Password:       hashedPassword,
			IsActive:       isActive,
			IsSuperuser:    isSuperuser,
			SessionVersion: 0,
		}
		if err := tx.Create(user).Error; err != nil {
			return err
		}
		return replaceUserRoles(tx, user.ID, roleIDs)
	})
}

func (s *Service) Update(ctx context.Context, actor *database.User, req updateUserRequest) error {
	var user database.User
	if err := s.db.WithContext(ctx).Where("id = ?", req.ID).First(&user).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return fmt.Errorf("用户不存在")
		}
		return err
	}

	updateData := map[string]interface{}{
		"updated_at": time.Now(),
	}

	if req.Email != nil {
		email := normalizeNullableString(*req.Email)
		if email != nil {
			exists, err := s.emailExists(ctx, *email, req.ID)
			if err != nil {
				return err
			}
			if exists {
				return fmt.Errorf("该邮箱地址已被其他用户使用")
			}
		}
		updateData["email"] = email
	}

	if req.Username != nil {
		username := strings.TrimSpace(*req.Username)
		exists, err := s.usernameExists(ctx, username, req.ID)
		if err != nil {
			return err
		}
		if exists {
			return fmt.Errorf("该用户名已被其他用户使用")
		}
		updateData["username"] = username
	}

	if req.Password != nil && strings.TrimSpace(*req.Password) != "" {
		return fmt.Errorf("请使用重置密码接口修改用户密码")
	}

	nextIsActive := user.IsActive
	if req.IsActive != nil {
		nextIsActive = *req.IsActive
		updateData["is_active"] = nextIsActive
	}
	if actor.ID == req.ID && !nextIsActive {
		return fmt.Errorf("不能禁用自己的账户")
	}

	nextIsSuperuser := user.IsSuperuser
	if req.IsSuperuser != nil {
		nextIsSuperuser = *req.IsSuperuser
		updateData["is_superuser"] = nextIsSuperuser
	}

	if req.Nickname != nil {
		updateData["nickname"] = normalizeStringPtr(req.Nickname)
	}
	if req.Phone != nil {
		updateData["phone"] = normalizeStringPtr(req.Phone)
	}

	var roleIDs []int64
	if req.RoleIDs != nil {
		roleIDs = append([]int64(nil), req.RoleIDs...)
		if err := s.ensureRolesExist(ctx, roleIDs); err != nil {
			return err
		}
	}
	if err := s.authz.EnsureCanUpdateUser(ctx, actor, &user, nextIsSuperuser, roleIDs); err != nil {
		return err
	}

	return s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if len(updateData) > 0 {
			if err := tx.Model(&user).Updates(updateData).Error; err != nil {
				return err
			}
		}
		if req.RoleIDs != nil {
			if err := replaceUserRoles(tx, user.ID, roleIDs); err != nil {
				return err
			}
		}
		return nil
	})
}

func (s *Service) Delete(ctx context.Context, actor *database.User, userID int64) error {
	if actor.ID == userID {
		return fmt.Errorf("不能删除自己的账户")
	}
	var user database.User
	if err := s.db.WithContext(ctx).Where("id = ?", userID).First(&user).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return fmt.Errorf("要删除的用户不存在")
		}
		return err
	}
	if err := s.authz.EnsureCanManageUser(ctx, actor, &user, "删除"); err != nil {
		return err
	}
	if user.IsSuperuser {
		var superuserCount int64
		if err := s.db.WithContext(ctx).Model(&database.User{}).Where("is_superuser = ?", true).Count(&superuserCount).Error; err != nil {
			return err
		}
		if superuserCount <= 1 {
			return fmt.Errorf("不能删除最后一个超级管理员账户")
		}
	}
	return s.db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		if err := tx.Where("user_id = ?", userID).Delete(&database.UserRole{}).Error; err != nil {
			return err
		}
		return tx.Delete(&database.User{}, userID).Error
	})
}

func (s *Service) ResetPassword(ctx context.Context, actor *database.User, req resetPasswordRequest) error {
	var user database.User
	if err := s.db.WithContext(ctx).Where("id = ?", req.UserID).First(&user).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return fmt.Errorf("用户不存在")
		}
		return err
	}
	if user.IsSuperuser && actor.ID != req.UserID {
		return fmt.Errorf("不允许重置其他超级管理员密码")
	}
	if actor.ID != req.UserID {
		if err := s.authz.EnsureCanManageUser(ctx, actor, &user, "重置密码"); err != nil {
			return err
		}
	}
	if password.Verify(req.NewPassword, user.Password) {
		return fmt.Errorf("新密码不能与当前密码相同")
	}
	if err := s.authz.SecurityPolicy(ctx).Validate(req.NewPassword); err != nil {
		return fmt.Errorf("密码强度不足: %w", err)
	}
	hashedPassword, err := password.Hash(req.NewPassword)
	if err != nil {
		return err
	}
	return s.db.WithContext(ctx).Model(&user).Updates(map[string]interface{}{
		"password":          hashedPassword,
		"session_version":   user.SessionVersion + 1,
		"refresh_token_jti": nil,
		"updated_at":        time.Now(),
	}).Error
}

func (h *Handler) List(w http.ResponseWriter, r *http.Request) {
	page, pageSize := parsePageParams(r)
	username := strings.TrimSpace(r.URL.Query().Get("username"))
	nickname := strings.TrimSpace(r.URL.Query().Get("nickname"))
	email := strings.TrimSpace(r.URL.Query().Get("email"))

	items, total, err := h.service.List(r.Context(), page, pageSize, username, nickname, email)
	if err != nil {
		response.Error(w, http.StatusInternalServerError, "获取用户列表失败", nil)
		return
	}
	response.Success(w, items, "成功", map[string]interface{}{
		"total":     total,
		"page":      page,
		"page_size": pageSize,
	})
}

func (h *Handler) Get(w http.ResponseWriter, r *http.Request) {
	userID, err := parseInt64Query(r, "user_id")
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	item, svcErr := h.service.Get(r.Context(), userID)
	if svcErr != nil {
		response.Error(w, http.StatusBadRequest, svcErr.Error(), nil)
		return
	}
	response.Success(w, item, "成功", nil)
}

func (h *Handler) Create(w http.ResponseWriter, r *http.Request) {
	actor, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	var req createUserRequest
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
	var req updateUserRequest
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
	userID, err := parseInt64Query(r, "user_id")
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	if err := h.service.Delete(r.Context(), actor, userID); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, nil, "删除成功", nil)
}

func (h *Handler) ResetPassword(w http.ResponseWriter, r *http.Request) {
	actor, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	var req resetPasswordRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "请求参数无效", nil)
		return
	}
	if err := h.service.ResetPassword(r.Context(), actor, req); err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, nil, "密码更新成功", nil)
}

func (s *Service) loadRoleSummariesByUserIDs(ctx context.Context, userIDs []int64) (map[int64][]roleSummary, error) {
	result := make(map[int64][]roleSummary)
	if len(userIDs) == 0 {
		return result, nil
	}
	type row struct {
		UserID int64  `gorm:"column:user_id"`
		ID     int64  `gorm:"column:id"`
		Name   string `gorm:"column:name"`
	}
	var rows []row
	err := s.db.WithContext(ctx).Table("role").
		Select("user_role.user_id, role.id, role.name").
		Joins("JOIN user_role ON user_role.role_id = role.id").
		Where("user_role.user_id IN ?", userIDs).
		Order("role.id ASC").
		Scan(&rows).Error
	if err != nil {
		return nil, err
	}
	for _, row := range rows {
		result[row.UserID] = append(result[row.UserID], roleSummary{ID: row.ID, Name: row.Name})
	}
	return result, nil
}

func (s *Service) getRoleIDByName(ctx context.Context, name string) (int64, error) {
	var role database.Role
	if err := s.db.WithContext(ctx).Where("name = ?", name).First(&role).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return 0, fmt.Errorf("默认角色不存在，请先初始化基础角色")
		}
		return 0, err
	}
	return role.ID, nil
}

func (s *Service) ensureRolesExist(ctx context.Context, roleIDs []int64) error {
	if len(roleIDs) == 0 {
		return nil
	}
	var roles []database.Role
	if err := s.db.WithContext(ctx).Where("id IN ?", roleIDs).Find(&roles).Error; err != nil {
		return err
	}
	found := make(map[int64]struct{}, len(roles))
	for _, role := range roles {
		found[role.ID] = struct{}{}
	}
	missing := make([]string, 0)
	for _, roleID := range roleIDs {
		if _, ok := found[roleID]; !ok {
			missing = append(missing, fmt.Sprintf("%d", roleID))
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("角色不存在: %s", strings.Join(missing, ", "))
	}
	return nil
}

func (s *Service) emailExists(ctx context.Context, email string, excludeID int64) (bool, error) {
	var count int64
	query := s.db.WithContext(ctx).Model(&database.User{}).Where("email = ?", email)
	if excludeID > 0 {
		query = query.Where("id <> ?", excludeID)
	}
	if err := query.Count(&count).Error; err != nil {
		return false, err
	}
	return count > 0, nil
}

func (s *Service) usernameExists(ctx context.Context, username string, excludeID int64) (bool, error) {
	var count int64
	query := s.db.WithContext(ctx).Model(&database.User{}).Where("username = ?", username)
	if excludeID > 0 {
		query = query.Where("id <> ?", excludeID)
	}
	if err := query.Count(&count).Error; err != nil {
		return false, err
	}
	return count > 0, nil
}

func replaceUserRoles(tx *gorm.DB, userID int64, roleIDs []int64) error {
	if err := tx.Where("user_id = ?", userID).Delete(&database.UserRole{}).Error; err != nil {
		return err
	}
	for _, roleID := range roleIDs {
		if err := tx.Create(&database.UserRole{UserID: userID, RoleID: roleID}).Error; err != nil {
			return err
		}
	}
	return nil
}

func serializeUser(user database.User, roles []roleSummary) map[string]interface{} {
	return map[string]interface{}{
		"id":           user.ID,
		"username":     user.Username,
		"nickname":     stringPtrValue(user.Nickname),
		"avatar":       stringPtrValue(user.Avatar),
		"email":        stringPtrValue(user.Email),
		"phone":        stringPtrValue(user.Phone),
		"is_active":    user.IsActive,
		"is_superuser": user.IsSuperuser,
		"last_login":   formatTimePtr(user.LastLogin),
		"created_at":   user.CreatedAt.Format("2006-01-02 15:04:05"),
		"updated_at":   user.UpdatedAt.Format("2006-01-02 15:04:05"),
		"roles":        roles,
	}
}

func userIDs(users []database.User) []int64 {
	ids := make([]int64, 0, len(users))
	for _, user := range users {
		ids = append(ids, user.ID)
	}
	return ids
}

func normalizePage(page int, pageSize int) (int, int) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 10
	}
	if pageSize > 1000 {
		pageSize = 1000
	}
	return page, pageSize
}

func parsePageParams(r *http.Request) (int, int) {
	page := 1
	pageSize := 10
	if raw := strings.TrimSpace(r.URL.Query().Get("page")); raw != "" {
		fmt.Sscanf(raw, "%d", &page)
	}
	if raw := strings.TrimSpace(r.URL.Query().Get("page_size")); raw != "" {
		fmt.Sscanf(raw, "%d", &pageSize)
	}
	return normalizePage(page, pageSize)
}

func parseInt64Query(r *http.Request, key string) (int64, error) {
	var value int64
	raw := strings.TrimSpace(r.URL.Query().Get(key))
	if raw == "" {
		return 0, fmt.Errorf("缺少参数 %s", key)
	}
	if _, err := fmt.Sscanf(raw, "%d", &value); err != nil {
		return 0, fmt.Errorf("参数 %s 无效", key)
	}
	return value, nil
}

func normalizeNullableString(value string) *string {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return nil
	}
	return &trimmed
}

func normalizeStringPtr(value *string) *string {
	if value == nil {
		return nil
	}
	return normalizeNullableString(*value)
}

func stringPtrValue(value *string) interface{} {
	if value == nil {
		return nil
	}
	return *value
}

func formatTimePtr(value *time.Time) interface{} {
	if value == nil {
		return nil
	}
	return value.Format("2006-01-02 15:04:05")
}
