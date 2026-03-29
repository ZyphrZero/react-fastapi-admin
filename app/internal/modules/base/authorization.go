package base

import (
	"context"
	"fmt"
	"sort"
	"strings"

	"gorm.io/gorm"

	"react-go-admin/app/internal/platform/database"
)

type permissionScope struct {
	MenuPaths map[string]struct{}
	APIIDs    map[int64]struct{}
}

// CurrentUserFromContext returns the authenticated user attached by AuthMiddleware.
func CurrentUserFromContext(ctx context.Context) (*database.User, bool) {
	return currentUserFromContext(ctx)
}

// CheckPermission validates that the user can access the current API route.
func (s *Service) CheckPermission(ctx context.Context, user *database.User, method string, routePath string) error {
	if user == nil {
		return fmt.Errorf("未授权访问")
	}
	if user.IsSuperuser {
		return nil
	}
	permissions, err := s.UserAPI(ctx, user)
	if err != nil {
		return err
	}
	expected := strings.ToLower(method) + routePath
	for _, permission := range permissions {
		if permission == expected {
			return nil
		}
	}
	return fmt.Errorf("权限不足")
}

func newPermissionScope(menuPaths []string, apiIDs []int64) permissionScope {
	menuSet := make(map[string]struct{}, len(menuPaths))
	for _, path := range menuPaths {
		menuSet[path] = struct{}{}
	}
	apiSet := make(map[int64]struct{}, len(apiIDs))
	for _, apiID := range apiIDs {
		apiSet[apiID] = struct{}{}
	}
	return permissionScope{MenuPaths: menuSet, APIIDs: apiSet}
}

func (s permissionScope) includes(other permissionScope) bool {
	for path := range other.MenuPaths {
		if _, ok := s.MenuPaths[path]; !ok {
			return false
		}
	}
	for apiID := range other.APIIDs {
		if _, ok := s.APIIDs[apiID]; !ok {
			return false
		}
	}
	return true
}

func (s permissionScope) strictlyIncludes(other permissionScope) bool {
	if !s.includes(other) {
		return false
	}
	if len(s.MenuPaths) != len(other.MenuPaths) || len(s.APIIDs) != len(other.APIIDs) {
		return true
	}
	return false
}

func (s *Service) getUserScope(ctx context.Context, user *database.User) (permissionScope, error) {
	if user.IsSuperuser {
		return newPermissionScope([]string{"*"}, []int64{-1}), nil
	}
	menuPaths, err := s.listMenuPathsForUser(ctx, user.ID)
	if err != nil {
		return permissionScope{}, err
	}
	apiIDs, err := s.listAPIIDsForUser(ctx, user.ID)
	if err != nil {
		return permissionScope{}, err
	}
	return newPermissionScope(menuPaths, apiIDs), nil
}

func (s *Service) getScopeForRoleIDs(ctx context.Context, roleIDs []int64) (permissionScope, error) {
	if len(roleIDs) == 0 {
		return newPermissionScope(nil, nil), nil
	}
	var roles []database.Role
	if err := s.db.WithContext(ctx).Where("id IN ?", roleIDs).Find(&roles).Error; err != nil {
		return permissionScope{}, err
	}
	menuSet := make(map[string]struct{})
	apiSet := make(map[int64]struct{})
	for _, role := range roles {
		for _, path := range role.MenuPaths {
			menuSet[path] = struct{}{}
		}
		for _, apiID := range role.APIIDs {
			apiSet[apiID] = struct{}{}
		}
	}
	menuPaths := make([]string, 0, len(menuSet))
	apiIDs := make([]int64, 0, len(apiSet))
	for path := range menuSet {
		menuPaths = append(menuPaths, path)
	}
	for apiID := range apiSet {
		apiIDs = append(apiIDs, apiID)
	}
	sort.Strings(menuPaths)
	sort.Slice(apiIDs, func(i, j int) bool { return apiIDs[i] < apiIDs[j] })
	return newPermissionScope(menuPaths, apiIDs), nil
}

func getScopeForRole(role *database.Role) permissionScope {
	if role == nil {
		return newPermissionScope(nil, nil)
	}
	return newPermissionScope(role.MenuPaths, role.APIIDs)
}

// EnsureCanManageUser checks actor > target permission scope.
func (s *Service) EnsureCanManageUser(ctx context.Context, actor *database.User, target *database.User, action string) error {
	if actor == nil || target == nil {
		return fmt.Errorf("%s失败", action)
	}
	if actor.IsSuperuser {
		return nil
	}
	if target.IsSuperuser {
		return fmt.Errorf("不能操作超级管理员账户")
	}
	actorScope, err := s.getUserScope(ctx, actor)
	if err != nil {
		return err
	}
	targetScope, err := s.getUserScope(ctx, target)
	if err != nil {
		return err
	}
	if !actorScope.strictlyIncludes(targetScope) {
		return fmt.Errorf("不能%s同级或更高权限账户", action)
	}
	return nil
}

// EnsureCanCreateUser checks whether the actor can create the target user shape.
func (s *Service) EnsureCanCreateUser(ctx context.Context, actor *database.User, isSuperuser bool, roleIDs []int64) error {
	if actor.IsSuperuser {
		return nil
	}
	if isSuperuser {
		return fmt.Errorf("只有超级管理员可以授予超级管理员身份")
	}
	return s.ensureCanAssignRoleIDs(ctx, actor, roleIDs, "授予")
}

// EnsureCanUpdateUser checks whether the actor can update the target user shape.
func (s *Service) EnsureCanUpdateUser(ctx context.Context, actor *database.User, target *database.User, nextIsSuperuser bool, roleIDs []int64) error {
	if actor.IsSuperuser {
		return nil
	}
	if err := s.EnsureCanManageUser(ctx, actor, target, "修改"); err != nil {
		return err
	}
	if nextIsSuperuser {
		return fmt.Errorf("只有超级管理员可以授予超级管理员身份")
	}
	if roleIDs != nil {
		return s.ensureCanAssignRoleIDs(ctx, actor, roleIDs, "授予")
	}
	return nil
}

func (s *Service) ensureCanAssignRoleIDs(ctx context.Context, actor *database.User, roleIDs []int64, action string) error {
	if actor.IsSuperuser {
		return nil
	}
	actorScope, err := s.getUserScope(ctx, actor)
	if err != nil {
		return err
	}
	targetScope, err := s.getScopeForRoleIDs(ctx, roleIDs)
	if err != nil {
		return err
	}
	if !actorScope.strictlyIncludes(targetScope) {
		return fmt.Errorf("不能%s同级或更高权限角色", action)
	}
	return nil
}

// EnsureCanCreateRole checks whether the actor can create a role with this scope.
func (s *Service) EnsureCanCreateRole(ctx context.Context, actor *database.User, menuPaths []string, apiIDs []int64) error {
	if actor.IsSuperuser {
		return nil
	}
	actorScope, err := s.getUserScope(ctx, actor)
	if err != nil {
		return err
	}
	targetScope := newPermissionScope(menuPaths, apiIDs)
	if !actorScope.strictlyIncludes(targetScope) {
		return fmt.Errorf("不能创建同级或更高权限角色")
	}
	return nil
}

// EnsureCanManageRole checks whether the actor can manage this role.
func (s *Service) EnsureCanManageRole(ctx context.Context, actor *database.User, role *database.Role, action string) error {
	if actor.IsSuperuser {
		return nil
	}
	actorScope, err := s.getUserScope(ctx, actor)
	if err != nil {
		return err
	}
	roleScope := getScopeForRole(role)
	if !actorScope.strictlyIncludes(roleScope) {
		return fmt.Errorf("不能%s同级或更高权限角色", action)
	}
	return nil
}

// EnsureCanUpdateRole checks whether the actor can update this role to the next scope.
func (s *Service) EnsureCanUpdateRole(ctx context.Context, actor *database.User, currentRole *database.Role, nextMenuPaths []string, nextAPIIDs []int64) error {
	if actor.IsSuperuser {
		return nil
	}
	if err := s.EnsureCanManageRole(ctx, actor, currentRole, "修改"); err != nil {
		return err
	}
	actorScope, err := s.getUserScope(ctx, actor)
	if err != nil {
		return err
	}
	nextScope := newPermissionScope(nextMenuPaths, nextAPIIDs)
	if !actorScope.strictlyIncludes(nextScope) {
		return fmt.Errorf("不能修改为同级或更高权限角色")
	}
	return nil
}

func runInTx(ctx context.Context, db *gorm.DB, fn func(tx *gorm.DB) error) error {
	return db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		return fn(tx)
	})
}
