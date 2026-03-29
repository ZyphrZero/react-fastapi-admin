package database

import (
	"database/sql/driver"
	"encoding/json"
	"fmt"
	"time"
)

type JSONStringSlice []string

func (s JSONStringSlice) Value() (driver.Value, error) {
	if s == nil {
		return "[]", nil
	}
	bytes, err := json.Marshal([]string(s))
	if err != nil {
		return nil, err
	}
	return string(bytes), nil
}

func (s *JSONStringSlice) Scan(value interface{}) error {
	if value == nil {
		*s = JSONStringSlice{}
		return nil
	}
	var raw []byte
	switch typed := value.(type) {
	case []byte:
		raw = typed
	case string:
		raw = []byte(typed)
	default:
		raw = []byte{}
	}
	if len(raw) == 0 {
		*s = JSONStringSlice{}
		return nil
	}
	var decoded []string
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return err
	}
	*s = JSONStringSlice(decoded)
	return nil
}

type JSONInt64Slice []int64

func (s JSONInt64Slice) Value() (driver.Value, error) {
	if s == nil {
		return "[]", nil
	}
	bytes, err := json.Marshal([]int64(s))
	if err != nil {
		return nil, err
	}
	return string(bytes), nil
}

func (s *JSONInt64Slice) Scan(value interface{}) error {
	if value == nil {
		*s = JSONInt64Slice{}
		return nil
	}
	var raw []byte
	switch typed := value.(type) {
	case []byte:
		raw = typed
	case string:
		raw = []byte(typed)
	default:
		raw = []byte{}
	}
	if len(raw) == 0 {
		*s = JSONInt64Slice{}
		return nil
	}
	var decoded []int64
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return err
	}
	*s = JSONInt64Slice(decoded)
	return nil
}

type JSONBytes []byte

func (b JSONBytes) Value() (driver.Value, error) {
	if b == nil {
		return []byte("null"), nil
	}
	return []byte(b), nil
}

func (b *JSONBytes) Scan(value interface{}) error {
	if value == nil {
		*b = nil
		return nil
	}
	switch typed := value.(type) {
	case []byte:
		*b = append((*b)[:0], typed...)
		return nil
	case string:
		*b = append((*b)[:0], []byte(typed)...)
		return nil
	default:
		return fmt.Errorf("unsupported JSONBytes source %T", value)
	}
}

type User struct {
	ID              int64      `gorm:"column:id;primaryKey;autoIncrement"`
	CreatedAt       time.Time  `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt       time.Time  `gorm:"column:updated_at;autoUpdateTime"`
	Username        string     `gorm:"column:username;size:20;not null;uniqueIndex:uidx_user_username"`
	Nickname        *string    `gorm:"column:nickname;size:30;index:idx_user_nickname"`
	Avatar          *string    `gorm:"column:avatar;size:500"`
	Email           *string    `gorm:"column:email;size:255;uniqueIndex:uidx_user_email"`
	Phone           *string    `gorm:"column:phone;size:20;index:idx_user_phone"`
	Password        string     `gorm:"column:password;size:128"`
	IsActive        bool       `gorm:"column:is_active;not null;index:idx_user_is_active"`
	IsSuperuser     bool       `gorm:"column:is_superuser;not null;index:idx_user_is_superuser"`
	LastLogin       *time.Time `gorm:"column:last_login;index:idx_user_last_login"`
	SessionVersion  int        `gorm:"column:session_version;not null;index:idx_user_session_version"`
	RefreshTokenJTI *string    `gorm:"column:refresh_token_jti;size:32;index:idx_user_refresh_token_jti"`
}

func (User) TableName() string {
	return "user"
}

type Role struct {
	ID        int64           `gorm:"column:id;primaryKey;autoIncrement"`
	CreatedAt time.Time       `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt time.Time       `gorm:"column:updated_at;autoUpdateTime"`
	Name      string          `gorm:"column:name;size:20;not null;uniqueIndex:uidx_role_name"`
	Desc      *string         `gorm:"column:desc;size:500"`
	MenuPaths JSONStringSlice `gorm:"column:menu_paths;type:json;not null"`
	APIIDs    JSONInt64Slice  `gorm:"column:api_ids;type:json;not null"`
}

func (Role) TableName() string {
	return "role"
}

type APIRecord struct {
	ID        int64     `gorm:"column:id;primaryKey;autoIncrement"`
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt time.Time `gorm:"column:updated_at;autoUpdateTime"`
	Path      string    `gorm:"column:path;size:100;not null;index:idx_api_path"`
	Method    string    `gorm:"column:method;size:10;not null;index:idx_api_method"`
	Summary   string    `gorm:"column:summary;size:500;not null;index:idx_api_summary"`
	Tags      string    `gorm:"column:tags;size:100;not null;index:idx_api_tags"`
}

func (APIRecord) TableName() string {
	return "api"
}

type AuditLog struct {
	ID            int64           `gorm:"column:id;primaryKey;autoIncrement"`
	CreatedAt     time.Time       `gorm:"column:created_at;autoCreateTime;index:idx_audit_created_at"`
	UpdatedAt     time.Time       `gorm:"column:updated_at;autoUpdateTime"`
	UserID        int64           `gorm:"column:user_id;not null;index:idx_audit_user_id"`
	Username      string          `gorm:"column:username;size:64;not null;index:idx_audit_username"`
	Module        string          `gorm:"column:module;size:64;not null;index:idx_audit_module"`
	Summary       string          `gorm:"column:summary;size:128;not null;index:idx_audit_summary"`
	Method        string          `gorm:"column:method;size:10;not null;index:idx_audit_method"`
	Path          string          `gorm:"column:path;size:255;not null;index:idx_audit_path"`
	Status        int             `gorm:"column:status;not null;index:idx_audit_status"`
	ResponseTime  int             `gorm:"column:response_time;not null;index:idx_audit_response_time"`
	RequestArgs   JSONBytes       `gorm:"column:request_args;type:json"`
	ResponseBody  JSONBytes       `gorm:"column:response_body;type:json"`
	IPAddress     string          `gorm:"column:ip_address;size:64;not null;index:idx_audit_ip_address"`
	UserAgent     string          `gorm:"column:user_agent;size:512;not null;index:idx_audit_user_agent"`
	OperationType string          `gorm:"column:operation_type;size:32;not null;index:idx_audit_operation_type"`
	LogLevel      string          `gorm:"column:log_level;size:16;not null;index:idx_audit_log_level"`
	IsDeleted     bool            `gorm:"column:is_deleted;not null;index:idx_audit_is_deleted"`
}

func (AuditLog) TableName() string {
	return "audit_log"
}

type SystemSetting struct {
	ID          int64      `gorm:"column:id;primaryKey;autoIncrement"`
	CreatedAt   time.Time  `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt   time.Time  `gorm:"column:updated_at;autoUpdateTime"`
	Key         string     `gorm:"column:key;size:100;not null;uniqueIndex:uidx_system_setting_key"`
	Value       []byte     `gorm:"column:value;type:json;not null"`
	Description *string    `gorm:"column:description;size:255"`
}

func (SystemSetting) TableName() string {
	return "system_setting"
}

type UserRole struct {
	UserID int64 `gorm:"column:user_id;primaryKey;not null"`
	RoleID int64 `gorm:"column:role_id;primaryKey;not null"`
}

func (UserRole) TableName() string {
	return "user_role"
}

type RateLimitBucket struct {
	ID        int64     `gorm:"column:id;primaryKey;autoIncrement"`
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt time.Time `gorm:"column:updated_at;autoUpdateTime"`
	BucketKey string    `gorm:"column:bucket_key;size:255;not null;uniqueIndex:uidx_rate_limit_bucket_key"`
	Count     int       `gorm:"column:count;not null"`
	ExpiresAt int64     `gorm:"column:expires_at;not null;index:idx_rate_limit_expires_at"`
}

func (RateLimitBucket) TableName() string {
	return "rate_limit_bucket"
}

type SchemaMigration struct {
	Version   int64     `gorm:"column:version;primaryKey"`
	Name      string    `gorm:"column:name;size:255;not null"`
	AppliedAt time.Time `gorm:"column:applied_at;not null"`
}

func (SchemaMigration) TableName() string {
	return "schema_migrations"
}
