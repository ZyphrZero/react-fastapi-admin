package upload

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/aliyun/aliyun-oss-go-sdk/oss"
	"gorm.io/gorm"

	"react-go-admin/app/internal/config"
	"react-go-admin/app/internal/modules/base"
	"react-go-admin/app/internal/platform/database"
	"react-go-admin/app/internal/platform/response"
)

const (
	maxUploadSize    = 10 * 1024 * 1024
	maxUploadFiles   = 10
	storageConfigKey = "storage_config"
)

var imageExtensions = map[string]struct{}{
	".jpg":  {},
	".jpeg": {},
	".png":  {},
	".gif":  {},
	".webp": {},
}

type storageSettings struct {
	Provider           string `json:"provider"`
	LocalUploadDir     string `json:"local_upload_dir"`
	LocalFullURL       string `json:"local_full_url"`
	OSSAccessKeyID     string `json:"oss_access_key_id"`
	OSSAccessKeySecret string `json:"oss_access_key_secret"`
	OSSBucketName      string `json:"oss_bucket_name"`
	OSSEndpoint        string `json:"oss_endpoint"`
	OSSBucketDomain    string `json:"oss_bucket_domain"`
	OSSUploadDir       string `json:"oss_upload_dir"`
}

type Service struct {
	cfg *config.Config
	db  *gorm.DB
}

type Handler struct {
	service *Service
}

func NewService(cfg *config.Config, db *gorm.DB) *Service {
	return &Service{cfg: cfg, db: db}
}

func NewHandler(service *Service) *Handler {
	return &Handler{service: service}
}

func (s *Service) UploadImage(ctx context.Context, file *multipart.FileHeader) (map[string]interface{}, error) {
	fileContent, err := validateImage(file)
	if err != nil {
		return nil, err
	}
	filename := generateFilename(file.Filename, "")
	url, err := s.storeFile(ctx, fileContent, filename, "image")
	if err != nil {
		return nil, err
	}
	return map[string]interface{}{
		"url":  url,
		"name": file.Filename,
		"size": len(fileContent),
	}, nil
}

func (s *Service) UploadAvatar(ctx context.Context, file *multipart.FileHeader) (map[string]interface{}, error) {
	fileContent, err := validateImage(file)
	if err != nil {
		return nil, err
	}
	extension := strings.ToLower(filepath.Ext(file.Filename))
	if extension == "" {
		extension = ".webp"
	}
	filename := generateFilename(file.Filename, extension)
	url, err := s.storeFile(ctx, fileContent, filename, "avatar")
	if err != nil {
		return nil, err
	}
	return map[string]interface{}{
		"url":  url,
		"name": filename,
		"size": len(fileContent),
	}, nil
}

func (s *Service) UploadFiles(ctx context.Context, files []*multipart.FileHeader) ([]map[string]interface{}, error) {
	if len(files) == 0 {
		return nil, fmt.Errorf("没有提供要上传的文件")
	}
	if len(files) > maxUploadFiles {
		return nil, fmt.Errorf("一次最多上传%d个文件", maxUploadFiles)
	}

	results := make([]map[string]interface{}, 0, len(files))
	for _, file := range files {
		fileContent, err := validateFile(file)
		if err != nil {
			return nil, err
		}
		fileType := detectFileType(file.Filename)
		filename := generateFilename(file.Filename, "")
		url, err := s.storeFile(ctx, fileContent, filename, fileType)
		if err != nil {
			return nil, err
		}
		results = append(results, map[string]interface{}{
			"url":  url,
			"name": file.Filename,
			"size": len(fileContent),
		})
	}
	return results, nil
}

func (s *Service) ListFiles(ctx context.Context, prefix string, maxKeys int) ([]map[string]interface{}, error) {
	settings, err := s.loadStorageSettings(ctx)
	if err != nil {
		return nil, err
	}
	if settings.Provider == "oss" {
		return s.listOSSFiles(settings, prefix, maxKeys)
	}
	return []map[string]interface{}{}, nil
}

func (s *Service) DeleteFile(ctx context.Context, fileKey string) (bool, error) {
	settings, err := s.loadStorageSettings(ctx)
	if err != nil {
		return false, err
	}
	if settings.Provider == "oss" && !isLocalFileKey(fileKey, settings) {
		return s.deleteOSSFile(settings, fileKey)
	}
	return deleteLocalFile(fileKey, settings, s.storageRoot()), nil
}

func (s *Service) SetPublicACL(ctx context.Context, actor *database.User, prefix string) (map[string]interface{}, error) {
	if actor == nil || !actor.IsSuperuser {
		return nil, fmt.Errorf("只有管理员才能执行此操作")
	}
	settings, err := s.loadStorageSettings(ctx)
	if err != nil {
		return nil, err
	}
	if settings.Provider != "oss" {
		return map[string]interface{}{
			"success":     false,
			"message":     "当前未启用对象存储",
			"count":       0,
			"error_count": 0,
		}, nil
	}
	return s.setOSSPublicACL(settings, prefix)
}

func (h *Handler) UploadImage(w http.ResponseWriter, r *http.Request) {
	uploaded, file, err := r.FormFile("file")
	if err != nil {
		response.Error(w, http.StatusBadRequest, "缺少上传文件", nil)
		return
	}
	_ = uploaded.Close()
	result, svcErr := h.service.UploadImage(r.Context(), file)
	if svcErr != nil {
		response.Error(w, http.StatusBadRequest, svcErr.Error(), nil)
		return
	}
	response.Success(w, result, "成功", nil)
}

func (h *Handler) UploadAvatar(w http.ResponseWriter, r *http.Request) {
	uploaded, file, err := r.FormFile("file")
	if err != nil {
		response.Error(w, http.StatusBadRequest, "缺少上传文件", nil)
		return
	}
	_ = uploaded.Close()
	result, svcErr := h.service.UploadAvatar(r.Context(), file)
	if svcErr != nil {
		response.Error(w, http.StatusBadRequest, svcErr.Error(), nil)
		return
	}
	response.Success(w, result, "成功", nil)
}

func (h *Handler) UploadFiles(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseMultipartForm(32 << 20); err != nil {
		response.Error(w, http.StatusBadRequest, "上传表单解析失败", nil)
		return
	}
	files := r.MultipartForm.File["files"]
	result, svcErr := h.service.UploadFiles(r.Context(), files)
	if svcErr != nil {
		response.Error(w, http.StatusBadRequest, svcErr.Error(), nil)
		return
	}
	response.Success(w, result, "成功", nil)
}

func (h *Handler) ListFiles(w http.ResponseWriter, r *http.Request) {
	maxKeys := 100
	if raw := strings.TrimSpace(r.URL.Query().Get("max_keys")); raw != "" {
		fmt.Sscanf(raw, "%d", &maxKeys)
	}
	result, err := h.service.ListFiles(r.Context(), strings.TrimSpace(r.URL.Query().Get("prefix")), maxKeys)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, result, "成功", nil)
}

func (h *Handler) DeleteFile(w http.ResponseWriter, r *http.Request) {
	fileKey := strings.TrimSpace(r.URL.Query().Get("file_key"))
	if fileKey == "" {
		response.Error(w, http.StatusBadRequest, "缺少参数 file_key", nil)
		return
	}
	result, err := h.service.DeleteFile(r.Context(), fileKey)
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, result, "成功", nil)
}

func (h *Handler) SetPublicACL(w http.ResponseWriter, r *http.Request) {
	actor, ok := base.CurrentUserFromContext(r.Context())
	if !ok {
		response.Error(w, http.StatusUnauthorized, "未授权访问", nil)
		return
	}
	result, err := h.service.SetPublicACL(r.Context(), actor, strings.TrimSpace(r.URL.Query().Get("prefix")))
	if err != nil {
		response.Error(w, http.StatusBadRequest, err.Error(), nil)
		return
	}
	response.Success(w, result, "成功", nil)
}

func (s *Service) loadStorageSettings(ctx context.Context) (storageSettings, error) {
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
	var setting database.SystemSetting
	if err := s.db.WithContext(ctx).Where("key = ?", storageConfigKey).Limit(1).Find(&setting).Error; err != nil {
		return current, err
	}
	if len(setting.Value) > 0 {
		if err := json.Unmarshal(setting.Value, &current); err != nil {
			return current, err
		}
	}
	current.LocalUploadDir = normalizeDir(current.LocalUploadDir, "uploads")
	current.OSSUploadDir = normalizeDir(current.OSSUploadDir, "uploads")
	return current, nil
}

func (s *Service) storeFile(ctx context.Context, content []byte, filename string, fileType string) (string, error) {
	settings, err := s.loadStorageSettings(ctx)
	if err != nil {
		return "", err
	}
	if settings.Provider == "oss" {
		return s.storeOSS(content, filename, settings, fileType)
	}
	return s.storeLocal(content, filename, settings, fileType)
}

func (s *Service) storeLocal(content []byte, filename string, settings storageSettings, fileType string) (string, error) {
	datePath := time.Now().Format("20060102")
	rootDir := filepath.Join(s.storageRoot(), settings.LocalUploadDir, fileType, datePath)
	if err := os.MkdirAll(rootDir, 0o755); err != nil {
		return "", fmt.Errorf("创建存储目录失败: %w", err)
	}
	fullPath := filepath.Join(rootDir, filename)
	if err := os.WriteFile(fullPath, content, 0o644); err != nil {
		return "", fmt.Errorf("上传到本地存储失败: %w", err)
	}

	urlPath := filepath.ToSlash(filepath.Join("/static", settings.LocalUploadDir, fileType, datePath, filename))
	if strings.TrimSpace(settings.LocalFullURL) != "" {
		relative := strings.TrimPrefix(urlPath, "/static/")
		return strings.TrimRight(settings.LocalFullURL, "/") + "/" + strings.TrimLeft(relative, "/"), nil
	}
	return urlPath, nil
}

func (s *Service) storeOSS(content []byte, filename string, settings storageSettings, fileType string) (string, error) {
	bucket, err := s.ossBucket(settings)
	if err != nil {
		return "", err
	}
	objectKey := strings.TrimLeft(filepath.ToSlash(filepath.Join(settings.OSSUploadDir, fileType, time.Now().Format("20060102"), filename)), "/")
	if err := bucket.PutObject(objectKey, bytes.NewReader(content), oss.ObjectACL(oss.ACLPublicRead)); err != nil {
		return "", fmt.Errorf("上传到对象存储失败: %w", err)
	}
	return buildOSSURL(settings, objectKey), nil
}

func (s *Service) storageRoot() string {
	return filepath.Join(s.cfg.BaseDir, "storage")
}

func validateImage(file *multipart.FileHeader) ([]byte, error) {
	extension := strings.ToLower(filepath.Ext(file.Filename))
	if _, ok := imageExtensions[extension]; !ok {
		return nil, fmt.Errorf("不支持的图片格式，仅支持: .jpg, .jpeg, .png, .gif, .webp")
	}
	return readFileContent(file, maxUploadSize)
}

func validateFile(file *multipart.FileHeader) ([]byte, error) {
	return readFileContent(file, maxUploadSize)
}

func readFileContent(file *multipart.FileHeader, maxSize int) ([]byte, error) {
	if file.Size > int64(maxSize) {
		return nil, fmt.Errorf("文件大小超出限制，最大允许10MB")
	}
	src, err := file.Open()
	if err != nil {
		return nil, fmt.Errorf("读取上传文件失败: %w", err)
	}
	defer src.Close()
	content, err := io.ReadAll(io.LimitReader(src, int64(maxSize)+1))
	if err != nil {
		return nil, fmt.Errorf("读取上传文件失败: %w", err)
	}
	if len(content) > maxSize {
		return nil, fmt.Errorf("文件大小超出限制，最大允许10MB")
	}
	return content, nil
}

func detectFileType(filename string) string {
	switch strings.ToLower(filepath.Ext(filename)) {
	case ".jpg", ".jpeg", ".png", ".gif", ".webp":
		return "image"
	case ".doc", ".docx", ".pdf", ".txt", ".xls", ".xlsx":
		return "document"
	case ".mp4", ".avi", ".mov", ".wmv":
		return "video"
	default:
		return "common"
	}
}

func generateFilename(original string, extensionOverride string) string {
	extension := extensionOverride
	if extension == "" {
		extension = strings.ToLower(filepath.Ext(original))
	}
	return time.Now().Format("20060102150405") + "_" + randomSuffix() + extension
}

func randomSuffix() string {
	buffer := make([]byte, 4)
	if _, err := rand.Read(buffer); err != nil {
		return "fallback"
	}
	return hex.EncodeToString(buffer)
}

func normalizeDir(value string, fallback string) string {
	trimmed := strings.Trim(strings.TrimSpace(value), "/")
	if trimmed == "" {
		return fallback
	}
	return trimmed
}

func isLocalFileKey(fileKey string, settings storageSettings) bool {
	fullURL := strings.TrimRight(strings.TrimSpace(settings.LocalFullURL), "/")
	return strings.HasPrefix(fileKey, "/static/") || (fullURL != "" && strings.HasPrefix(fileKey, fullURL))
}

func deleteLocalFile(fileKey string, settings storageSettings, storageRoot string) bool {
	fullURL := strings.TrimRight(strings.TrimSpace(settings.LocalFullURL), "/")
	relativePath := ""
	switch {
	case fullURL != "" && strings.HasPrefix(fileKey, fullURL):
		relativePath = strings.TrimLeft(strings.TrimPrefix(fileKey, fullURL), "/")
	case strings.HasPrefix(fileKey, "/static/"):
		relativePath = strings.TrimLeft(strings.TrimPrefix(fileKey, "/static/"), "/")
	default:
		return false
	}

	cleanRoot := filepath.Clean(storageRoot)
	targetPath := filepath.Clean(filepath.Join(cleanRoot, relativePath))
	if !strings.HasPrefix(targetPath, cleanRoot) {
		return false
	}
	if _, err := os.Stat(targetPath); err != nil {
		return false
	}
	_ = os.Remove(targetPath)
	return true
}

func (s *Service) listOSSFiles(settings storageSettings, prefix string, maxKeys int) ([]map[string]interface{}, error) {
	bucket, err := s.ossBucket(settings)
	if err != nil {
		return nil, err
	}
	fullPrefix := strings.TrimLeft(filepath.ToSlash(filepath.Join(settings.OSSUploadDir, prefix)), "/")
	if strings.TrimSpace(prefix) == "" {
		fullPrefix = strings.TrimLeft(filepath.ToSlash(settings.OSSUploadDir), "/")
	}
	if maxKeys <= 0 {
		maxKeys = 100
	}
	if maxKeys > 1000 {
		maxKeys = 1000
	}
	result, err := bucket.ListObjectsV2(oss.Prefix(fullPrefix), oss.MaxKeys(maxKeys))
	if err != nil {
		return nil, fmt.Errorf("获取文件列表失败: %w", err)
	}
	items := make([]map[string]interface{}, 0, len(result.Objects))
	for _, object := range result.Objects {
		if strings.HasSuffix(object.Key, "/") {
			continue
		}
		items = append(items, map[string]interface{}{
			"name":          filepath.Base(object.Key),
			"url":           buildOSSURL(settings, object.Key),
			"key":           object.Key,
			"size":          object.Size,
			"last_modified": object.LastModified.Format("2006-01-02 15:04:05"),
		})
	}
	return items, nil
}

func (s *Service) deleteOSSFile(settings storageSettings, fileKey string) (bool, error) {
	bucket, err := s.ossBucket(settings)
	if err != nil {
		return false, err
	}
	objectKey, err := extractOSSObjectKey(fileKey, settings)
	if err != nil {
		return false, err
	}
	if err := bucket.DeleteObject(objectKey); err != nil {
		return false, fmt.Errorf("删除文件失败: %w", err)
	}
	return true, nil
}

func (s *Service) setOSSPublicACL(settings storageSettings, prefix string) (map[string]interface{}, error) {
	bucket, err := s.ossBucket(settings)
	if err != nil {
		return nil, err
	}
	fullPrefix := strings.TrimLeft(filepath.ToSlash(filepath.Join(settings.OSSUploadDir, prefix)), "/")
	if strings.TrimSpace(prefix) == "" {
		fullPrefix = strings.TrimLeft(filepath.ToSlash(settings.OSSUploadDir), "/")
	}
	result, err := bucket.ListObjectsV2(oss.Prefix(fullPrefix), oss.MaxKeys(1000))
	if err != nil {
		return nil, fmt.Errorf("设置文件ACL失败: %w", err)
	}
	count := 0
	errorCount := 0
	for _, object := range result.Objects {
		if strings.HasSuffix(object.Key, "/") {
			continue
		}
		if err := bucket.SetObjectACL(object.Key, oss.ACLPublicRead); err != nil {
			errorCount++
			continue
		}
		count++
	}
	return map[string]interface{}{
		"success":     true,
		"message":     fmt.Sprintf("成功设置 %d 个文件的ACL为公共读，失败 %d 个", count, errorCount),
		"count":       count,
		"error_count": errorCount,
	}, nil
}

func (s *Service) ossBucket(settings storageSettings) (*oss.Bucket, error) {
	if strings.TrimSpace(settings.OSSAccessKeyID) == "" || strings.TrimSpace(settings.OSSAccessKeySecret) == "" || strings.TrimSpace(settings.OSSBucketName) == "" || strings.TrimSpace(settings.OSSEndpoint) == "" {
		return nil, fmt.Errorf("对象存储配置不完整，缺少: AccessKey ID、AccessKey Secret、Bucket 名称或 Endpoint")
	}
	endpoint := normalizeOSSEndpoint(settings.OSSEndpoint)
	client, err := oss.New(endpoint, settings.OSSAccessKeyID, settings.OSSAccessKeySecret)
	if err != nil {
		return nil, fmt.Errorf("初始化对象存储客户端失败: %w", err)
	}
	bucket, err := client.Bucket(settings.OSSBucketName)
	if err != nil {
		return nil, fmt.Errorf("初始化对象存储 Bucket 失败: %w", err)
	}
	return bucket, nil
}

func normalizeOSSEndpoint(endpoint string) string {
	endpoint = strings.TrimSpace(endpoint)
	if strings.HasPrefix(endpoint, "http://") || strings.HasPrefix(endpoint, "https://") {
		return endpoint
	}
	return "https://" + endpoint
}

func buildOSSURL(settings storageSettings, objectKey string) string {
	objectKey = strings.TrimLeft(objectKey, "/")
	if domain := strings.TrimSpace(settings.OSSBucketDomain); domain != "" {
		if strings.HasPrefix(domain, "http://") || strings.HasPrefix(domain, "https://") {
			return strings.TrimRight(domain, "/") + "/" + objectKey
		}
		return "https://" + strings.TrimRight(domain, "/") + "/" + objectKey
	}
	endpoint := strings.TrimRight(normalizeOSSEndpoint(settings.OSSEndpoint), "/")
	return fmt.Sprintf("%s/%s", strings.Replace(endpoint, "://", "://"+settings.OSSBucketName+".", 1), objectKey)
}

func extractOSSObjectKey(fileKey string, settings storageSettings) (string, error) {
	fileKey = strings.TrimSpace(fileKey)
	if fileKey == "" {
		return "", fmt.Errorf("无效的对象存储文件路径")
	}
	if !strings.Contains(fileKey, "://") {
		return strings.TrimLeft(fileKey, "/"), nil
	}
	parsed, err := url.Parse(fileKey)
	if err != nil {
		return "", fmt.Errorf("无效的对象存储文件路径")
	}
	return strings.TrimLeft(parsed.Path, "/"), nil
}
