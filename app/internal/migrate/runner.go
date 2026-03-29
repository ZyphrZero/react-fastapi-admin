package migrate

import (
	"context"
	"fmt"
	"sort"
	"time"

	"gorm.io/gorm"

	"react-go-admin/app/internal/platform/database"
)

type Migration struct {
	Version int64
	Name    string
	Up      func(context.Context, *gorm.DB) error
	Down    func(context.Context, *gorm.DB) error
}

type Status struct {
	Version int64
	Name    string
	Applied bool
}

var migrations = []Migration{
	{
		Version: 202603290001,
		Name:    "initial_schema",
		Up:      upInitialSchema,
		Down:    downInitialSchema,
	},
}

func Up(ctx context.Context, db *gorm.DB) error {
	if err := ensureMetadataTable(ctx, db); err != nil {
		return err
	}
	applied, err := appliedVersions(ctx, db)
	if err != nil {
		return err
	}
	for _, migration := range migrations {
		if _, ok := applied[migration.Version]; ok {
			continue
		}
		if err := db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
			if err := migration.Up(ctx, tx); err != nil {
				return err
			}
			return tx.Create(&database.SchemaMigration{
				Version:   migration.Version,
				Name:      migration.Name,
				AppliedAt: time.Now(),
			}).Error
		}); err != nil {
			return fmt.Errorf("apply migration %d_%s: %w", migration.Version, migration.Name, err)
		}
	}
	return nil
}

func Down(ctx context.Context, db *gorm.DB, steps int) error {
	if steps < 1 {
		steps = 1
	}
	if err := ensureMetadataTable(ctx, db); err != nil {
		return err
	}
	var applied []database.SchemaMigration
	if err := db.WithContext(ctx).Order("version DESC").Limit(steps).Find(&applied).Error; err != nil {
		return err
	}
	if len(applied) == 0 {
		return nil
	}
	migrationMap := make(map[int64]Migration, len(migrations))
	for _, migration := range migrations {
		migrationMap[migration.Version] = migration
	}
	for _, appliedMigration := range applied {
		migration, ok := migrationMap[appliedMigration.Version]
		if !ok || migration.Down == nil {
			return fmt.Errorf("no rollback registered for migration %d", appliedMigration.Version)
		}
		if err := db.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
			if err := migration.Down(ctx, tx); err != nil {
				return err
			}
			return tx.Delete(&database.SchemaMigration{}, "version = ?", appliedMigration.Version).Error
		}); err != nil {
			return fmt.Errorf("rollback migration %d_%s: %w", migration.Version, migration.Name, err)
		}
	}
	return nil
}

func Statuses(ctx context.Context, db *gorm.DB) ([]Status, error) {
	if err := ensureMetadataTable(ctx, db); err != nil {
		return nil, err
	}
	applied, err := appliedVersions(ctx, db)
	if err != nil {
		return nil, err
	}
	statuses := make([]Status, 0, len(migrations))
	for _, migration := range migrations {
		_, ok := applied[migration.Version]
		statuses = append(statuses, Status{
			Version: migration.Version,
			Name:    migration.Name,
			Applied: ok,
		})
	}
	sort.Slice(statuses, func(i, j int) bool { return statuses[i].Version < statuses[j].Version })
	return statuses, nil
}

func ensureMetadataTable(ctx context.Context, db *gorm.DB) error {
	return db.WithContext(ctx).AutoMigrate(&database.SchemaMigration{})
}

func appliedVersions(ctx context.Context, db *gorm.DB) (map[int64]struct{}, error) {
	var rows []database.SchemaMigration
	if err := db.WithContext(ctx).Find(&rows).Error; err != nil {
		return nil, err
	}
	result := make(map[int64]struct{}, len(rows))
	for _, row := range rows {
		result[row.Version] = struct{}{}
	}
	return result, nil
}

func upInitialSchema(ctx context.Context, db *gorm.DB) error {
	return db.WithContext(ctx).AutoMigrate(
		&database.User{},
		&database.Role{},
		&database.APIRecord{},
		&database.AuditLog{},
		&database.SystemSetting{},
		&database.UserRole{},
		&database.RateLimitBucket{},
	)
}

func downInitialSchema(ctx context.Context, db *gorm.DB) error {
	return db.WithContext(ctx).Migrator().DropTable(
		&database.RateLimitBucket{},
		&database.UserRole{},
		&database.SystemSetting{},
		&database.AuditLog{},
		&database.APIRecord{},
		&database.Role{},
		&database.User{},
	)
}
