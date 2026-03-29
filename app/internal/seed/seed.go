package seed

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"gorm.io/gorm"

	"react-go-admin/app/internal/catalog"
	"react-go-admin/app/internal/config"
	"react-go-admin/app/internal/modules/base"
	"react-go-admin/app/internal/platform/database"
	"react-go-admin/app/internal/platform/password"
)

func Run(ctx context.Context, cfg *config.Config, logger *slog.Logger, db *gorm.DB) error {
	if err := catalog.Sync(ctx, db); err != nil {
		return err
	}
	if err := ensureRoles(ctx, db); err != nil {
		return err
	}
	adminUser, generatedPassword, err := ensureAdmin(ctx, cfg, db)
	if err != nil {
		return err
	}
	if err := ensureAdminRoleAssignment(ctx, cfg, db, adminUser); err != nil {
		return err
	}
	if err := syncDefaultRolePermissions(ctx, db); err != nil {
		return err
	}
	if generatedPassword != "" && logger != nil {
		logger.Warn("bootstrap admin password generated automatically", "username", cfg.InitialAdminUsername, "password", generatedPassword)
	}
	return nil
}

func ensureRoles(ctx context.Context, db *gorm.DB) error {
	defaultRoles := []struct {
		Name string
		Desc string
	}{
		{Name: "管理员", Desc: "管理员角色"},
		{Name: "普通用户", Desc: "普通用户角色"},
	}

	for _, roleDef := range defaultRoles {
		var existing database.Role
		err := db.WithContext(ctx).Where("name = ?", roleDef.Name).First(&existing).Error
		if err == nil {
			continue
		}
		if err != nil && err != gorm.ErrRecordNotFound {
			return err
		}

		desc := roleDef.Desc
		role := database.Role{
			Name:      roleDef.Name,
			Desc:      &desc,
			MenuPaths: database.JSONStringSlice(base.DefaultRoleMenuPaths(roleDef.Name)),
			APIIDs:    database.JSONInt64Slice{},
		}
		if err := db.WithContext(ctx).Create(&role).Error; err != nil {
			return err
		}
	}
	return nil
}

func ensureAdmin(ctx context.Context, cfg *config.Config, db *gorm.DB) (*database.User, string, error) {
	var existingByUsername database.User
	err := db.WithContext(ctx).Where("username = ?", cfg.InitialAdminUsername).First(&existingByUsername).Error
	if err == nil {
		if existingByUsername.IsSuperuser {
			return &existingByUsername, "", nil
		}
		return nil, "", fmt.Errorf("username %s already exists but is not superuser", cfg.InitialAdminUsername)
	}
	if err != nil && err != gorm.ErrRecordNotFound {
		return nil, "", err
	}

	policy := password.NewPolicy(cfg)
	initialPassword := strings.TrimSpace(cfg.InitialAdminPassword)
	generatedPassword := ""
	if initialPassword == "" {
		var err error
		initialPassword, err = password.GenerateBootstrapPassword(12)
		if err != nil {
			return nil, "", err
		}
		generatedPassword = initialPassword
	} else if err := policy.Validate(initialPassword); err != nil {
		return nil, "", fmt.Errorf("INITIAL_ADMIN_PASSWORD 不满足密码策略: %w", err)
	}

	hashedPassword, err := password.Hash(initialPassword)
	if err != nil {
		return nil, "", err
	}
	user := &database.User{
		Username:       cfg.InitialAdminUsername,
		Email:          stringPtr(strings.TrimSpace(cfg.InitialAdminEmail)),
		Nickname:       stringPtr(strings.TrimSpace(cfg.InitialAdminNickname)),
		Password:       hashedPassword,
		IsActive:       true,
		IsSuperuser:    true,
		SessionVersion: 0,
		CreatedAt:      time.Now(),
		UpdatedAt:      time.Now(),
	}
	if err := db.WithContext(ctx).Create(user).Error; err != nil {
		return nil, "", err
	}
	return user, generatedPassword, nil
}

func ensureAdminRoleAssignment(ctx context.Context, cfg *config.Config, db *gorm.DB, adminUser *database.User) error {
	if adminUser == nil {
		return nil
	}
	var adminRole database.Role
	if err := db.WithContext(ctx).Where("name = ?", "管理员").First(&adminRole).Error; err != nil {
		return err
	}
	var count int64
	if err := db.WithContext(ctx).Model(&database.UserRole{}).Where("user_id = ? AND role_id = ?", adminUser.ID, adminRole.ID).Count(&count).Error; err != nil {
		return err
	}
	if count > 0 {
		return nil
	}
	return db.WithContext(ctx).Create(&database.UserRole{UserID: adminUser.ID, RoleID: adminRole.ID}).Error
}

func syncDefaultRolePermissions(ctx context.Context, db *gorm.DB) error {
	var allAPIs []database.APIRecord
	if err := db.WithContext(ctx).Order("id ASC").Find(&allAPIs).Error; err != nil {
		return err
	}
	allAPIIDs := make([]int64, 0, len(allAPIs))
	for _, api := range allAPIs {
		allAPIIDs = append(allAPIIDs, api.ID)
	}
	for _, roleName := range []string{"管理员", "普通用户"} {
		var role database.Role
		if err := db.WithContext(ctx).Where("name = ?", roleName).First(&role).Error; err != nil {
			return err
		}
		updates := map[string]interface{}{"updated_at": time.Now()}
		changed := false
		if len(role.MenuPaths) == 0 {
			updates["menu_paths"] = database.JSONStringSlice(base.DefaultRoleMenuPaths(roleName))
			changed = true
		}
		if roleName == "管理员" && len(role.APIIDs) == 0 {
			updates["api_ids"] = database.JSONInt64Slice(allAPIIDs)
			changed = true
		}
		if roleName == "普通用户" && role.APIIDs == nil {
			updates["api_ids"] = database.JSONInt64Slice{}
			changed = true
		}
		if changed {
			if err := db.WithContext(ctx).Model(&role).Updates(updates).Error; err != nil {
				return err
			}
		}
	}
	return nil
}

func stringPtr(value string) *string {
	if value == "" {
		return nil
	}
	return &value
}
