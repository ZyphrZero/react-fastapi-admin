import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AppWindowIcon,
  CloudIcon,
  FileTextIcon,
  ImageUpIcon,
  LockKeyholeIcon,
  LogsIcon,
  RotateCcwIcon,
  SaveIcon,
  ServerCogIcon,
  ShieldIcon,
  LinkIcon,
} from 'lucide-react'

import api from '@/api'
import { LoginPageImageStage } from '@/components/LoginPageImageStage'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { useErrorHandler } from '@/hooks/useErrorHandler'
import { dispatchAppMetaUpdated } from '@/utils/appMeta'

const defaultApplicationValues = {
  app_title: 'React FastAPI Admin',
  project_name: 'React FastAPI Admin',
  app_description: 'React FastAPI Admin Description',
  debug: false,
  environment: 'dev',
  login_page_image_url: '',
  login_page_image_mode: 'contain',
  notification_position: 'top-right',
  notification_duration: '4000',
  notification_visible_toasts: '3',
}

const defaultLoginPageImage = '/login-panel-illustration.svg'
const loginPageImageModeOptions = [
  { value: 'cover', label: '填充' },
  { value: 'contain', label: '适应' },
  { value: 'fill', label: '拉伸' },
  { value: 'repeat', label: '平铺' },
]

const notificationPositionOptions = [
  { value: 'top-left', label: '左上角' },
  { value: 'top-center', label: '顶部居中' },
  { value: 'top-right', label: '右上角' },
  { value: 'bottom-left', label: '左下角' },
  { value: 'bottom-center', label: '底部居中' },
  { value: 'bottom-right', label: '右下角' },
]

const defaultLoggingValues = {
  logs_root: 'app/logs',
  log_retention_days: '7',
  log_rotation: '1 day',
  log_max_file_size: '10 MB',
  log_enable_access_log: true,
  access_log_requires_restart: true,
}

const defaultSecurityValues = {
  password_min_length: '8',
  password_require_uppercase: true,
  password_require_lowercase: true,
  password_require_digits: true,
  password_require_special: true,
  rate_limit_enabled: true,
  rate_limit_max_requests: '60',
  rate_limit_window_seconds: '60',
  ip_whitelist: '',
}

const defaultStorageValues = {
  provider: 'local',
  local_upload_dir: 'uploads',
  local_full_url: '',
  oss_access_key_id: '',
  oss_access_key_secret: '',
  oss_bucket_name: '',
  oss_endpoint: '',
  oss_bucket_domain: '',
  oss_upload_dir: 'uploads',
}

const maxLoginPageImageSize = 10 * 1024 * 1024

const localFieldConfig = [
  { key: 'local_upload_dir', label: '本地上传目录', placeholder: '例如 uploads' },
  { key: 'local_full_url', label: '本地完整访问地址', placeholder: '可选，例如 https://files.example.com' },
]

const ossFieldConfig = [
  { key: 'oss_access_key_id', label: 'AccessKey ID', placeholder: '请输入 AccessKey ID' },
  { key: 'oss_access_key_secret', label: 'AccessKey Secret', placeholder: '请输入 AccessKey Secret', type: 'password' },
  { key: 'oss_bucket_name', label: 'Bucket 名称', placeholder: '例如 media-assets' },
  { key: 'oss_endpoint', label: 'Endpoint', placeholder: '例如 oss-cn-hangzhou.aliyuncs.com' },
  { key: 'oss_bucket_domain', label: '自定义域名', placeholder: '可选，例如 cdn.example.com' },
  { key: 'oss_upload_dir', label: '上传目录', placeholder: '例如 uploads' },
]

const normalizeWhitelistItems = (value = '') =>
  String(value)
    .replace(/\r\n/g, '\n')
    .split(/[\n,;]/)
    .map((item) => item.trim())
    .filter(Boolean)

const validateApplicationSettings = (values) => {
  const errors = {}
  const notificationDuration = Number(values.notification_duration)
  const notificationVisibleToasts = Number(values.notification_visible_toasts)
  if (!values.app_title.trim()) errors.app_title = '请填写应用标题'
  if (!values.project_name.trim()) errors.project_name = '请填写项目名称'
  if (!values.app_description.trim()) errors.app_description = '请填写应用描述'
  if (!Number.isInteger(notificationDuration) || notificationDuration < 1000 || notificationDuration > 60000) {
    errors.notification_duration = '通知时长必须为 1000 到 60000 之间的整数'
  }
  if (!Number.isInteger(notificationVisibleToasts) || notificationVisibleToasts < 1 || notificationVisibleToasts > 10) {
    errors.notification_visible_toasts = '同时显示数量必须为 1 到 10 之间的整数'
  }
  return errors
}

const validateLoggingSettings = (values) => {
  const errors = {}
  const retentionDays = Number(values.log_retention_days)

  if (!values.logs_root.trim()) errors.logs_root = '请填写日志目录'
  if (!Number.isInteger(retentionDays) || retentionDays < 1 || retentionDays > 3650) {
    errors.log_retention_days = '日志保留天数必须为 1 到 3650 之间的整数'
  }
  if (!values.log_rotation.trim()) errors.log_rotation = '请填写日志轮转周期'
  if (!values.log_max_file_size.trim()) errors.log_max_file_size = '请填写单个日志文件大小限制'
  return errors
}

const validateSecuritySettings = (values) => {
  const errors = {}
  const passwordMinLength = Number(values.password_min_length)
  const maxRequests = Number(values.rate_limit_max_requests)
  const windowSeconds = Number(values.rate_limit_window_seconds)

  if (!Number.isInteger(passwordMinLength) || passwordMinLength < 6 || passwordMinLength > 72) {
    errors.password_min_length = '密码最小长度必须为 6 到 72 之间的整数'
  }
  if (!Number.isInteger(maxRequests) || maxRequests < 1) {
    errors.rate_limit_max_requests = '最大请求数必须为大于 0 的整数'
  }
  if (!Number.isInteger(windowSeconds) || windowSeconds < 1) {
    errors.rate_limit_window_seconds = '时间窗口必须为大于 0 的整数'
  }
  return errors
}

const validateStorageSettings = (values) => {
  const errors = {}
  if (!values.local_upload_dir.trim()) errors.local_upload_dir = '请填写本地上传目录'
  if (!values.oss_upload_dir.trim()) errors.oss_upload_dir = '请填写上传目录'

  if (values.provider === 'oss') {
    if (!values.oss_access_key_id.trim()) errors.oss_access_key_id = '启用对象存储时必须填写 AccessKey ID'
    if (!values.oss_access_key_secret.trim()) errors.oss_access_key_secret = '启用对象存储时必须填写 AccessKey Secret'
    if (!values.oss_bucket_name.trim()) errors.oss_bucket_name = '启用对象存储时必须填写 Bucket 名称'
    if (!values.oss_endpoint.trim()) errors.oss_endpoint = '启用对象存储时必须填写 Endpoint'
  }

  return errors
}

const SettingBadge = ({ label, value }) => (
  <div className="rounded-lg border bg-background px-3 py-2 text-sm text-muted-foreground">
    <span className="mr-2">{label}</span>
    <span className="font-medium text-foreground">{value}</span>
  </div>
)

const ToggleField = ({ description, label, onCheckedChange, checked }) => (
  <div className="flex items-center justify-between rounded-lg border bg-muted/20 p-3">
    <div>
      <div className="text-sm font-medium">{label}</div>
      {description ? <div className="text-xs text-muted-foreground">{description}</div> : null}
    </div>
    <Switch checked={checked} onCheckedChange={onCheckedChange} />
  </div>
)

const SystemSettings = () => {
  const [applicationValues, setApplicationValues] = useState(defaultApplicationValues)
  const [loggingValues, setLoggingValues] = useState(defaultLoggingValues)
  const [securityValues, setSecurityValues] = useState(defaultSecurityValues)
  const [storageValues, setStorageValues] = useState(defaultStorageValues)
  const [applicationErrors, setApplicationErrors] = useState({})
  const [loggingErrors, setLoggingErrors] = useState({})
  const [securityErrors, setSecurityErrors] = useState({})
  const [storageErrors, setStorageErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [savingSection, setSavingSection] = useState('')
  const [uploadingLoginImage, setUploadingLoginImage] = useState(false)
  const loginImageInputRef = useRef(null)

  const { handleBusinessError, handleError, showSuccess, showWarning } = useErrorHandler()
  const provider = storageValues.provider || 'local'
  const whitelistCount = useMemo(() => normalizeWhitelistItems(securityValues.ip_whitelist).length, [securityValues.ip_whitelist])
  const loginPageImagePreview = applicationValues.login_page_image_url?.trim() || defaultLoginPageImage

  const fetchSystemSettings = useCallback(async () => {
    setLoading(true)
    try {
      const [applicationResponse, loggingResponse, securityResponse, storageResponse] = await Promise.all([
        api.systemSettings.getApplicationSettings(),
        api.systemSettings.getLoggingSettings(),
        api.systemSettings.getSecuritySettings(),
        api.systemSettings.getStorageSettings(),
      ])

      const applicationData = applicationResponse.data || {}
      const loggingData = loggingResponse.data || {}
      const securityData = securityResponse.data || {}
      const storageData = storageResponse.data || {}

      setApplicationValues({
        app_title: applicationData.app_title || defaultApplicationValues.app_title,
        project_name: applicationData.project_name || defaultApplicationValues.project_name,
        app_description: applicationData.app_description || defaultApplicationValues.app_description,
        debug: Boolean(applicationData.debug),
        environment: applicationData.environment || defaultApplicationValues.environment,
        login_page_image_url: applicationData.login_page_image_url || '',
        login_page_image_mode: applicationData.login_page_image_mode || defaultApplicationValues.login_page_image_mode,
        notification_position: applicationData.notification_position || defaultApplicationValues.notification_position,
        notification_duration: String(applicationData.notification_duration || defaultApplicationValues.notification_duration),
        notification_visible_toasts: String(
          applicationData.notification_visible_toasts || defaultApplicationValues.notification_visible_toasts
        ),
      })
      setLoggingValues({
        logs_root: loggingData.logs_root || defaultLoggingValues.logs_root,
        log_retention_days: String(loggingData.log_retention_days || defaultLoggingValues.log_retention_days),
        log_rotation: loggingData.log_rotation || defaultLoggingValues.log_rotation,
        log_max_file_size: loggingData.log_max_file_size || defaultLoggingValues.log_max_file_size,
        log_enable_access_log: loggingData.log_enable_access_log ?? defaultLoggingValues.log_enable_access_log,
        access_log_requires_restart: loggingData.access_log_requires_restart ?? true,
      })
      setSecurityValues({
        password_min_length: String(securityData.password_min_length || defaultSecurityValues.password_min_length),
        password_require_uppercase: securityData.password_require_uppercase ?? defaultSecurityValues.password_require_uppercase,
        password_require_lowercase: securityData.password_require_lowercase ?? defaultSecurityValues.password_require_lowercase,
        password_require_digits: securityData.password_require_digits ?? defaultSecurityValues.password_require_digits,
        password_require_special: securityData.password_require_special ?? defaultSecurityValues.password_require_special,
        rate_limit_enabled: securityData.rate_limit_enabled ?? defaultSecurityValues.rate_limit_enabled,
        rate_limit_max_requests: String(securityData.rate_limit_max_requests || defaultSecurityValues.rate_limit_max_requests),
        rate_limit_window_seconds: String(securityData.rate_limit_window_seconds || defaultSecurityValues.rate_limit_window_seconds),
        ip_whitelist: securityData.ip_whitelist || '',
      })
      setStorageValues({
        provider: storageData.provider || defaultStorageValues.provider,
        local_upload_dir: storageData.local_upload_dir || defaultStorageValues.local_upload_dir,
        local_full_url: storageData.local_full_url || '',
        oss_access_key_id: storageData.oss_access_key_id || '',
        oss_access_key_secret: storageData.oss_access_key_secret || '',
        oss_bucket_name: storageData.oss_bucket_name || '',
        oss_endpoint: storageData.oss_endpoint || '',
        oss_bucket_domain: storageData.oss_bucket_domain || '',
        oss_upload_dir: storageData.oss_upload_dir || defaultStorageValues.oss_upload_dir,
      })
    } catch (error) {
      handleError(error, '获取系统设置失败')
    } finally {
      setLoading(false)
    }
  }, [handleError])

  useEffect(() => {
    void fetchSystemSettings()
  }, [fetchSystemSettings])

  const updateApplicationField = (field, value) => {
    setApplicationValues((current) => ({ ...current, [field]: value }))
    setApplicationErrors((current) => ({ ...current, [field]: undefined }))
  }

  const updateLoggingField = (field, value) => {
    setLoggingValues((current) => ({ ...current, [field]: value }))
    setLoggingErrors((current) => ({ ...current, [field]: undefined }))
  }

  const updateSecurityField = (field, value) => {
    setSecurityValues((current) => ({ ...current, [field]: value }))
    setSecurityErrors((current) => ({ ...current, [field]: undefined }))
  }

  const updateStorageField = (field, value) => {
    setStorageValues((current) => ({ ...current, [field]: value }))
    setStorageErrors((current) => ({ ...current, [field]: undefined }))
  }

  const saveApplicationSettings = async (event) => {
    event.preventDefault()
    const nextErrors = validateApplicationSettings(applicationValues)
    if (Object.keys(nextErrors).length > 0) {
      setApplicationErrors(nextErrors)
      return
    }

    setSavingSection('application')
    try {
      const payload = {
        app_title: applicationValues.app_title.trim(),
        project_name: applicationValues.project_name.trim(),
        app_description: applicationValues.app_description.trim(),
        debug: applicationValues.debug,
        login_page_image_url: applicationValues.login_page_image_url.trim(),
        login_page_image_mode: applicationValues.login_page_image_mode || defaultApplicationValues.login_page_image_mode,
        notification_position: applicationValues.notification_position || defaultApplicationValues.notification_position,
        notification_duration: Number(applicationValues.notification_duration),
        notification_visible_toasts: Number(applicationValues.notification_visible_toasts),
      }
      const response = await api.systemSettings.updateApplicationSettings(payload)
      const data = response.data || payload

      setApplicationValues((current) => ({
        ...current,
        app_title: data.app_title || payload.app_title,
        project_name: data.project_name || payload.project_name,
        app_description: data.app_description || payload.app_description,
        debug: Boolean(data.debug),
        login_page_image_url: data.login_page_image_url || payload.login_page_image_url,
        login_page_image_mode: data.login_page_image_mode || payload.login_page_image_mode,
        notification_position: data.notification_position || payload.notification_position,
        notification_duration: String(data.notification_duration || payload.notification_duration),
        notification_visible_toasts: String(data.notification_visible_toasts || payload.notification_visible_toasts),
      }))
      dispatchAppMetaUpdated({
        app_title: data.app_title || payload.app_title,
        project_name: data.project_name || payload.project_name,
        app_description: data.app_description || payload.app_description,
        login_page_image_url: data.login_page_image_url || payload.login_page_image_url,
        login_page_image_mode: data.login_page_image_mode || payload.login_page_image_mode,
        notification_position: data.notification_position || payload.notification_position,
        notification_duration: data.notification_duration || payload.notification_duration,
        notification_visible_toasts: data.notification_visible_toasts || payload.notification_visible_toasts,
      })
      showSuccess('基础设置已保存')
    } catch (error) {
      handleBusinessError(error, '保存基础设置失败')
    } finally {
      setSavingSection('')
    }
  }

  const saveLoggingSettings = async (event) => {
    event.preventDefault()
    const nextErrors = validateLoggingSettings(loggingValues)
    if (Object.keys(nextErrors).length > 0) {
      setLoggingErrors(nextErrors)
      return
    }

    setSavingSection('logging')
    try {
      const payload = {
        logs_root: loggingValues.logs_root.trim(),
        log_retention_days: Number(loggingValues.log_retention_days),
        log_rotation: loggingValues.log_rotation.trim(),
        log_max_file_size: loggingValues.log_max_file_size.trim(),
        log_enable_access_log: loggingValues.log_enable_access_log,
      }
      const response = await api.systemSettings.updateLoggingSettings(payload)
      const data = response.data || payload

      setLoggingValues({
        logs_root: data.logs_root || payload.logs_root,
        log_retention_days: String(data.log_retention_days || payload.log_retention_days),
        log_rotation: data.log_rotation || payload.log_rotation,
        log_max_file_size: data.log_max_file_size || payload.log_max_file_size,
        log_enable_access_log: Boolean(data.log_enable_access_log),
        access_log_requires_restart: data.access_log_requires_restart ?? true,
      })
      showSuccess('日志设置已保存')
    } catch (error) {
      handleBusinessError(error, '保存日志设置失败')
    } finally {
      setSavingSection('')
    }
  }

  const saveSecuritySettings = async (event) => {
    event.preventDefault()
    const nextErrors = validateSecuritySettings(securityValues)
    if (Object.keys(nextErrors).length > 0) {
      setSecurityErrors(nextErrors)
      return
    }

    setSavingSection('security')
    try {
      const payload = {
        password_min_length: Number(securityValues.password_min_length),
        password_require_uppercase: securityValues.password_require_uppercase,
        password_require_lowercase: securityValues.password_require_lowercase,
        password_require_digits: securityValues.password_require_digits,
        password_require_special: securityValues.password_require_special,
        rate_limit_enabled: securityValues.rate_limit_enabled,
        rate_limit_max_requests: Number(securityValues.rate_limit_max_requests),
        rate_limit_window_seconds: Number(securityValues.rate_limit_window_seconds),
        ip_whitelist: securityValues.ip_whitelist,
      }
      const response = await api.systemSettings.updateSecuritySettings(payload)
      const data = response.data || payload

      setSecurityValues((current) => ({
        ...current,
        password_min_length: String(data.password_min_length || payload.password_min_length),
        password_require_uppercase: Boolean(data.password_require_uppercase),
        password_require_lowercase: Boolean(data.password_require_lowercase),
        password_require_digits: Boolean(data.password_require_digits),
        password_require_special: Boolean(data.password_require_special),
        rate_limit_enabled: Boolean(data.rate_limit_enabled),
        rate_limit_max_requests: String(data.rate_limit_max_requests || payload.rate_limit_max_requests),
        rate_limit_window_seconds: String(data.rate_limit_window_seconds || payload.rate_limit_window_seconds),
        ip_whitelist: data.ip_whitelist || '',
      }))
      showSuccess('安全设置已保存')
    } catch (error) {
      handleBusinessError(error, '保存安全设置失败')
    } finally {
      setSavingSection('')
    }
  }

  const saveStorageSettings = async (event) => {
    event.preventDefault()
    const nextErrors = validateStorageSettings(storageValues)
    if (Object.keys(nextErrors).length > 0) {
      setStorageErrors(nextErrors)
      return
    }

    setSavingSection('storage')
    try {
      const payload = { ...storageValues, provider }
      const response = await api.systemSettings.updateStorageSettings(payload)
      const data = response.data || payload

      setStorageValues({
        provider: data.provider || defaultStorageValues.provider,
        local_upload_dir: data.local_upload_dir || defaultStorageValues.local_upload_dir,
        local_full_url: data.local_full_url || '',
        oss_access_key_id: data.oss_access_key_id || '',
        oss_access_key_secret: data.oss_access_key_secret || '',
        oss_bucket_name: data.oss_bucket_name || '',
        oss_endpoint: data.oss_endpoint || '',
        oss_bucket_domain: data.oss_bucket_domain || '',
        oss_upload_dir: data.oss_upload_dir || defaultStorageValues.oss_upload_dir,
      })
      showSuccess('存储设置已保存')
    } catch (error) {
      handleBusinessError(error, '保存存储设置失败')
    } finally {
      setSavingSection('')
    }
  }

  const triggerLoginImageUpload = () => {
    loginImageInputRef.current?.click()
  }

  const restoreDefaultLoginImage = () => {
    updateApplicationField('login_page_image_url', '')
  }

  const handleLoginImageUpload = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''

    if (!file) {
      return
    }

    if (!file.type.startsWith('image/')) {
      showWarning('请选择图片文件')
      return
    }

    if (file.size > maxLoginPageImageSize) {
      showWarning('登录页图片不能超过 10MB')
      return
    }

    setUploadingLoginImage(true)
    try {
      const response = await api.upload.uploadImage(file)
      const nextUrl = response.data?.url || ''

      if (!nextUrl) {
        showWarning('图片上传成功，但没有返回可用地址')
        return
      }

      updateApplicationField('login_page_image_url', nextUrl)
      showSuccess('登录页图片上传成功')
    } catch (error) {
      handleBusinessError(error, '登录页图片上传失败')
    } finally {
      setUploadingLoginImage(false)
    }
  }

  const statusBadges = useMemo(
    () => [
      { label: '当前环境', value: applicationValues.environment || defaultApplicationValues.environment },
      { label: '调试模式', value: applicationValues.debug ? '已启用' : '已关闭' },
      { label: '登录页图片', value: applicationValues.login_page_image_url ? '已自定义' : '默认插画' },
      {
        label: '图片模式',
        value: loginPageImageModeOptions.find((item) => item.value === applicationValues.login_page_image_mode)?.label || '适应',
      },
      {
        label: '通知位置',
        value: notificationPositionOptions.find((item) => item.value === applicationValues.notification_position)?.label || '右上角',
      },
      { label: '日志目录', value: loggingValues.logs_root || defaultLoggingValues.logs_root },
      {
        label: '限流',
        value: securityValues.rate_limit_enabled
          ? `${securityValues.rate_limit_max_requests}/${securityValues.rate_limit_window_seconds}s`
          : '已关闭',
      },
      { label: 'IP 白名单', value: whitelistCount > 0 ? `${whitelistCount} 项` : '未启用' },
      { label: '存储模式', value: provider === 'oss' ? '对象存储' : '本地存储' },
    ],
    [
      applicationValues.debug,
      applicationValues.environment,
      applicationValues.login_page_image_url,
      applicationValues.login_page_image_mode,
      applicationValues.notification_position,
      loggingValues.logs_root,
      provider,
      securityValues.rate_limit_enabled,
      securityValues.rate_limit_max_requests,
      securityValues.rate_limit_window_seconds,
      whitelistCount,
    ],
  )

  const loadingContent = <div className="text-sm text-muted-foreground">加载中...</div>

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-3 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">系统设置</h1>
          <p className="text-sm text-muted-foreground">管理应用信息、日志参数、安全策略和存储配置</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {statusBadges.map((item) => (
            <SettingBadge key={item.label} label={item.label} value={item.value} />
          ))}
        </div>
      </section>

      <Tabs defaultValue="application">
        <TabsList>
          <TabsTrigger value="application">基础设置</TabsTrigger>
          <TabsTrigger value="logging">日志配置</TabsTrigger>
          <TabsTrigger value="security">安全策略</TabsTrigger>
          <TabsTrigger value="storage">存储设置</TabsTrigger>
        </TabsList>

        <TabsContent value="application">
          <Card>
            <CardHeader>
              <CardTitle>基础设置</CardTitle>
              <CardDescription>配置系统名称、项目名称、描述、调试模式和通知展示策略</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? loadingContent : (
                <form className="flex flex-col gap-6" onSubmit={saveApplicationSettings}>
                  <div className="grid gap-4 xl:grid-cols-2">
                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <AppWindowIcon className="size-4" />
                          应用标识
                        </CardTitle>
                        <CardDescription>影响工作台、OpenAPI 标题和服务基础信息展示</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <FieldGroup className="grid gap-4">
                          <Field data-invalid={Boolean(applicationErrors.app_title)}>
                            <FieldLabel htmlFor="system-app-title" required>APP_TITLE</FieldLabel>
                            <Input id="system-app-title" value={applicationValues.app_title} onChange={(event) => updateApplicationField('app_title', event.target.value)} aria-invalid={Boolean(applicationErrors.app_title)} />
                            <FieldError>{applicationErrors.app_title}</FieldError>
                          </Field>
                          <Field data-invalid={Boolean(applicationErrors.project_name)}>
                            <FieldLabel htmlFor="system-project-name" required>PROJECT_NAME</FieldLabel>
                            <Input id="system-project-name" value={applicationValues.project_name} onChange={(event) => updateApplicationField('project_name', event.target.value)} aria-invalid={Boolean(applicationErrors.project_name)} />
                            <FieldError>{applicationErrors.project_name}</FieldError>
                          </Field>
                          <Field data-invalid={Boolean(applicationErrors.app_description)}>
                            <FieldLabel htmlFor="system-app-description" required>APP_DESCRIPTION</FieldLabel>
                            <Textarea id="system-app-description" value={applicationValues.app_description} onChange={(event) => updateApplicationField('app_description', event.target.value)} aria-invalid={Boolean(applicationErrors.app_description)} />
                            <FieldError>{applicationErrors.app_description}</FieldError>
                          </Field>
                        </FieldGroup>
                      </CardContent>
                    </Card>

                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <FileTextIcon className="size-4" />
                          运行与通知
                        </CardTitle>
                        <CardDescription>调试模式会影响日志级别和诊断输出，通知相关设置会立即影响全局提示</CardDescription>
                      </CardHeader>
                      <CardContent className="flex flex-col gap-4">
                        <Field>
                          <FieldLabel htmlFor="application-environment">当前环境</FieldLabel>
                          <Input
                            id="application-environment"
                            value={applicationValues.environment}
                            disabled
                            readOnly
                          />
                        </Field>
                        <ToggleField label="DEBUG" description="生产环境下后端会拒绝启用调试模式" checked={applicationValues.debug} onCheckedChange={(checked) => updateApplicationField('debug', checked)} />
                        <Field>
                          <FieldLabel htmlFor="notification-position">通知显示位置</FieldLabel>
                          <Select
                            value={applicationValues.notification_position}
                            onValueChange={(value) => updateApplicationField('notification_position', value)}
                          >
                            <SelectTrigger id="notification-position" className="w-full">
                              <SelectValue placeholder="请选择通知显示位置" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectGroup>
                                {notificationPositionOptions.map((item) => (
                                  <SelectItem key={item.value} value={item.value}>
                                    {item.label}
                                  </SelectItem>
                                ))}
                              </SelectGroup>
                            </SelectContent>
                          </Select>
                        </Field>
                        <Field data-invalid={Boolean(applicationErrors.notification_duration)}>
                          <FieldLabel htmlFor="notification-duration" required>通知显示时长（毫秒）</FieldLabel>
                          <Input
                            id="notification-duration"
                            type="number"
                            min="1000"
                            max="60000"
                            value={applicationValues.notification_duration}
                            onChange={(event) => updateApplicationField('notification_duration', event.target.value)}
                            aria-invalid={Boolean(applicationErrors.notification_duration)}
                          />
                          <FieldError>{applicationErrors.notification_duration}</FieldError>
                        </Field>
                        <Field data-invalid={Boolean(applicationErrors.notification_visible_toasts)}>
                          <FieldLabel htmlFor="notification-visible-toasts" required>最大同时显示数</FieldLabel>
                          <Input
                            id="notification-visible-toasts"
                            type="number"
                            min="1"
                            max="10"
                            value={applicationValues.notification_visible_toasts}
                            onChange={(event) => updateApplicationField('notification_visible_toasts', event.target.value)}
                            aria-invalid={Boolean(applicationErrors.notification_visible_toasts)}
                          />
                          <FieldError>{applicationErrors.notification_visible_toasts}</FieldError>
                        </Field>
                      </CardContent>
                    </Card>
                  </div>

                  <Card size="sm">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <ImageUpIcon className="size-4" />
                        登录页图片
                      </CardTitle>
                      <CardDescription>支持填写外部 URL，或直接上传到当前存储。图片支持填充、适应、拉伸和平铺四种显示方式，预览与登录页使用同一套展示规则。</CardDescription>
                    </CardHeader>
                    <CardContent className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(20rem,0.9fr)]">
                      <div className="flex flex-col gap-4">
                        <Field>
                          <FieldLabel htmlFor="login-page-image-url">
                            <LinkIcon className="size-4" />
                            登录页图片地址
                          </FieldLabel>
                          <Input
                            id="login-page-image-url"
                            value={applicationValues.login_page_image_url}
                            placeholder="支持 https://... 或 /static/... 地址"
                            onChange={(event) => updateApplicationField('login_page_image_url', event.target.value)}
                          />
                        </Field>
                        <Field>
                          <FieldLabel htmlFor="login-page-image-mode">图片显示模式</FieldLabel>
                          <Select
                            value={applicationValues.login_page_image_mode}
                            onValueChange={(value) => updateApplicationField('login_page_image_mode', value)}
                          >
                            <SelectTrigger id="login-page-image-mode" className="w-full">
                              <SelectValue placeholder="请选择图片显示模式" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectGroup>
                                {loginPageImageModeOptions.map((item) => (
                                  <SelectItem key={item.value} value={item.value}>
                                    {item.label}
                                  </SelectItem>
                                ))}
                              </SelectGroup>
                            </SelectContent>
                          </Select>
                        </Field>

                        <input
                          ref={loginImageInputRef}
                          type="file"
                          accept="image/png,image/jpeg,image/webp,image/gif"
                          className="hidden"
                          onChange={(event) => void handleLoginImageUpload(event)}
                        />

                        <div className="flex flex-wrap gap-3">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={triggerLoginImageUpload}
                            disabled={uploadingLoginImage}
                          >
                            <ImageUpIcon data-icon="inline-start" />
                            {uploadingLoginImage ? '上传中...' : '上传图片到存储'}
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            onClick={restoreDefaultLoginImage}
                            disabled={!applicationValues.login_page_image_url}
                          >
                            <RotateCcwIcon data-icon="inline-start" />
                            恢复默认插画
                          </Button>
                        </div>

                        <div className="rounded-lg border bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
                          预览与登录页右侧卡片使用同一套展示比例和图片模式。填充会覆盖显示区域，适应会完整显示，拉伸会强制铺满，平铺会以固定块尺寸重复显示。上传图片会使用当前系统存储配置，本地存储和对象存储都可直接回填 URL。
                        </div>
                      </div>

                      <div className="flex flex-col gap-3">
                        <div className="text-sm font-medium">预览</div>
                        <div className="mx-auto flex aspect-[10/13] w-full max-w-[20rem] items-stretch justify-stretch overflow-hidden rounded-2xl border bg-stone-100/60 dark:bg-muted/10">
                          <LoginPageImageStage
                            src={loginPageImagePreview}
                            mode={applicationValues.login_page_image_mode}
                            alt="登录页图片预览"
                            fillParent
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={savingSection === 'application'}>
                      <SaveIcon data-icon="inline-start" />
                      {savingSection === 'application' ? '保存中...' : '保存基础设置'}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logging">
          <Card>
            <CardHeader>
              <CardTitle>日志配置</CardTitle>
              <CardDescription>管理日志目录、保留周期、轮转策略和访问日志开关</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? loadingContent : (
                <form className="flex flex-col gap-6" onSubmit={saveLoggingSettings}>
                  <div className="grid gap-4 xl:grid-cols-2">
                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <LogsIcon className="size-4" />
                          日志文件策略
                        </CardTitle>
                        <CardDescription>大部分日志参数保存后会立即生效</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <FieldGroup className="grid gap-4">
                          <Field data-invalid={Boolean(loggingErrors.logs_root)}>
                            <FieldLabel htmlFor="logs-root" required>LOGS_ROOT</FieldLabel>
                            <Input id="logs-root" value={loggingValues.logs_root} onChange={(event) => updateLoggingField('logs_root', event.target.value)} aria-invalid={Boolean(loggingErrors.logs_root)} />
                            <FieldError>{loggingErrors.logs_root}</FieldError>
                          </Field>
                          <Field data-invalid={Boolean(loggingErrors.log_retention_days)}>
                            <FieldLabel htmlFor="log-retention-days" required>LOG_RETENTION_DAYS</FieldLabel>
                            <Input id="log-retention-days" type="number" min="1" value={loggingValues.log_retention_days} onChange={(event) => updateLoggingField('log_retention_days', event.target.value)} aria-invalid={Boolean(loggingErrors.log_retention_days)} />
                            <FieldError>{loggingErrors.log_retention_days}</FieldError>
                          </Field>
                          <Field data-invalid={Boolean(loggingErrors.log_rotation)}>
                            <FieldLabel htmlFor="log-rotation" required>LOG_ROTATION</FieldLabel>
                            <Input id="log-rotation" value={loggingValues.log_rotation} onChange={(event) => updateLoggingField('log_rotation', event.target.value)} aria-invalid={Boolean(loggingErrors.log_rotation)} />
                            <FieldError>{loggingErrors.log_rotation}</FieldError>
                          </Field>
                          <Field data-invalid={Boolean(loggingErrors.log_max_file_size)}>
                            <FieldLabel htmlFor="log-max-file-size" required>LOG_MAX_FILE_SIZE</FieldLabel>
                            <Input id="log-max-file-size" value={loggingValues.log_max_file_size} onChange={(event) => updateLoggingField('log_max_file_size', event.target.value)} aria-invalid={Boolean(loggingErrors.log_max_file_size)} />
                            <FieldError>{loggingErrors.log_max_file_size}</FieldError>
                          </Field>
                        </FieldGroup>
                      </CardContent>
                    </Card>

                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <ServerCogIcon className="size-4" />
                          访问日志
                        </CardTitle>
                        <CardDescription>访问日志开关会影响中间件挂载行为</CardDescription>
                      </CardHeader>
                      <CardContent className="flex flex-col gap-4">
                        <ToggleField label="LOG_ENABLE_ACCESS_LOG" description={loggingValues.access_log_requires_restart ? '该开关保存后会持久化，重启应用后完全生效' : '该开关保存后立即生效'} checked={loggingValues.log_enable_access_log} onCheckedChange={(checked) => updateLoggingField('log_enable_access_log', checked)} />
                        {loggingValues.access_log_requires_restart ? <div className="rounded-lg border bg-muted/20 p-4 text-sm text-muted-foreground">当前实现中，访问日志中间件在应用启动时装配。修改此开关后，应用重启后会完全按新值工作。</div> : null}
                      </CardContent>
                    </Card>
                  </div>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={savingSection === 'logging'}>
                      <SaveIcon data-icon="inline-start" />
                      {savingSection === 'logging' ? '保存中...' : '保存日志设置'}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>安全策略</CardTitle>
              <CardDescription>配置密码策略、请求限流和 IP 白名单</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? loadingContent : (
                <form className="flex flex-col gap-6" onSubmit={saveSecuritySettings}>
                  <div className="grid gap-4 xl:grid-cols-2">
                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <LockKeyholeIcon className="size-4" />
                          密码策略
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <FieldGroup className="grid gap-4 md:grid-cols-2">
                          <Field data-invalid={Boolean(securityErrors.password_min_length)} className="md:col-span-2">
                            <FieldLabel htmlFor="password-min-length" required>最小长度</FieldLabel>
                            <Input id="password-min-length" type="number" min="6" max="72" value={securityValues.password_min_length} onChange={(event) => updateSecurityField('password_min_length', event.target.value)} aria-invalid={Boolean(securityErrors.password_min_length)} />
                            <FieldError>{securityErrors.password_min_length}</FieldError>
                          </Field>
                          <ToggleField label="要求大写字母" checked={securityValues.password_require_uppercase} onCheckedChange={(checked) => updateSecurityField('password_require_uppercase', checked)} />
                          <ToggleField label="要求小写字母" checked={securityValues.password_require_lowercase} onCheckedChange={(checked) => updateSecurityField('password_require_lowercase', checked)} />
                          <ToggleField label="要求数字" checked={securityValues.password_require_digits} onCheckedChange={(checked) => updateSecurityField('password_require_digits', checked)} />
                          <ToggleField label="要求特殊字符" checked={securityValues.password_require_special} onCheckedChange={(checked) => updateSecurityField('password_require_special', checked)} />
                        </FieldGroup>
                      </CardContent>
                    </Card>

                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <ShieldIcon className="size-4" />
                          访问控制
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="flex flex-col gap-4">
                        <ToggleField label="启用请求频率限制" description="关闭后将不再限制单位时间请求数" checked={securityValues.rate_limit_enabled} onCheckedChange={(checked) => updateSecurityField('rate_limit_enabled', checked)} />
                        <FieldGroup className="grid gap-4 md:grid-cols-2">
                          <Field data-invalid={Boolean(securityErrors.rate_limit_max_requests)}>
                            <FieldLabel htmlFor="rate-limit-max-requests" required>窗口最大请求数</FieldLabel>
                            <Input id="rate-limit-max-requests" type="number" min="1" value={securityValues.rate_limit_max_requests} onChange={(event) => updateSecurityField('rate_limit_max_requests', event.target.value)} aria-invalid={Boolean(securityErrors.rate_limit_max_requests)} />
                            <FieldError>{securityErrors.rate_limit_max_requests}</FieldError>
                          </Field>
                          <Field data-invalid={Boolean(securityErrors.rate_limit_window_seconds)}>
                            <FieldLabel htmlFor="rate-limit-window-seconds" required>时间窗口（秒）</FieldLabel>
                            <Input id="rate-limit-window-seconds" type="number" min="1" value={securityValues.rate_limit_window_seconds} onChange={(event) => updateSecurityField('rate_limit_window_seconds', event.target.value)} aria-invalid={Boolean(securityErrors.rate_limit_window_seconds)} />
                            <FieldError>{securityErrors.rate_limit_window_seconds}</FieldError>
                          </Field>
                        </FieldGroup>
                        <Field>
                          <FieldLabel htmlFor="ip-whitelist">IP 白名单</FieldLabel>
                          <Textarea id="ip-whitelist" value={securityValues.ip_whitelist} placeholder={'每行一个 IP，或使用逗号分隔\n例如：127.0.0.1\n192.168.1.10'} onChange={(event) => updateSecurityField('ip_whitelist', event.target.value)} />
                          <div className="mt-2 text-xs text-muted-foreground">当前识别到 {whitelistCount} 个白名单项；留空表示不限制来源 IP。</div>
                        </Field>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={savingSection === 'security'}>
                      <SaveIcon data-icon="inline-start" />
                      {savingSection === 'security' ? '保存中...' : '保存安全设置'}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="storage">
          <Card>
            <CardHeader>
              <CardTitle>存储设置</CardTitle>
              <CardDescription>切换存储模式后保存即可生效</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? loadingContent : (
                <form className="flex flex-col gap-6" onSubmit={saveStorageSettings}>
                  <div className="flex items-center justify-between rounded-lg border bg-muted/20 p-4">
                    <div className="flex items-start gap-3">
                      <ServerCogIcon className="mt-0.5 size-4 text-muted-foreground" />
                      <div>
                        <div className="text-sm font-medium">当前生效模式</div>
                        <div className="text-sm text-muted-foreground">当前为 {provider === 'oss' ? '对象存储' : '本地存储'}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground">本地</span>
                      <Switch checked={provider === 'oss'} onCheckedChange={(checked) => updateStorageField('provider', checked ? 'oss' : 'local')} />
                      <span className="text-sm text-muted-foreground">对象存储</span>
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <Card size="sm">
                      <CardHeader>
                        <CardTitle>本地存储</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <FieldGroup>
                          {localFieldConfig.map((field) => (
                            <Field key={field.key} data-invalid={Boolean(storageErrors[field.key])}>
                              <FieldLabel htmlFor={field.key} required={field.key === 'local_upload_dir'}>{field.label}</FieldLabel>
                              <Input id={field.key} value={storageValues[field.key]} required={field.key === 'local_upload_dir'} placeholder={field.placeholder} onChange={(event) => updateStorageField(field.key, event.target.value)} aria-invalid={Boolean(storageErrors[field.key])} />
                              <FieldError>{storageErrors[field.key]}</FieldError>
                            </Field>
                          ))}
                        </FieldGroup>
                      </CardContent>
                    </Card>

                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <CloudIcon className="size-4" />
                          对象存储
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <FieldGroup className="grid gap-4 md:grid-cols-2">
                          {ossFieldConfig.map((field) => (
                            <Field key={field.key} data-invalid={Boolean(storageErrors[field.key])} className={field.key === 'oss_bucket_domain' ? 'md:col-span-2' : undefined}>
                              <FieldLabel htmlFor={field.key} required={field.key === 'oss_upload_dir' || (provider === 'oss' && ['oss_access_key_id', 'oss_access_key_secret', 'oss_bucket_name', 'oss_endpoint'].includes(field.key))}>{field.label}</FieldLabel>
                              <Input id={field.key} type={field.type || 'text'} disabled={provider !== 'oss'} required={field.key === 'oss_upload_dir' || (provider === 'oss' && ['oss_access_key_id', 'oss_access_key_secret', 'oss_bucket_name', 'oss_endpoint'].includes(field.key))} value={storageValues[field.key]} placeholder={field.placeholder} onChange={(event) => updateStorageField(field.key, event.target.value)} aria-invalid={Boolean(storageErrors[field.key])} />
                              <FieldError>{storageErrors[field.key]}</FieldError>
                            </Field>
                          ))}
                        </FieldGroup>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={savingSection === 'storage'}>
                      <SaveIcon data-icon="inline-start" />
                      {savingSection === 'storage' ? '保存中...' : '保存存储设置'}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default SystemSettings
