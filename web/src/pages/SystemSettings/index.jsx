import { useCallback, useEffect, useMemo, useState } from 'react'
import { CloudIcon, FolderIcon, SaveIcon, ServerCogIcon } from 'lucide-react'

import api from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useErrorHandler } from '@/hooks/useErrorHandler'

const defaultValues = {
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

const validateSettings = (values) => {
  const errors = {}

  if (!values.local_upload_dir.trim()) {
    errors.local_upload_dir = '请填写本地上传目录'
  }

  if (!values.oss_upload_dir.trim()) {
    errors.oss_upload_dir = '请填写上传目录'
  }

  if (values.provider === 'oss') {
    if (!values.oss_access_key_id.trim()) errors.oss_access_key_id = '启用对象存储时必须填写 AccessKey ID'
    if (!values.oss_access_key_secret.trim()) errors.oss_access_key_secret = '启用对象存储时必须填写 AccessKey Secret'
    if (!values.oss_bucket_name.trim()) errors.oss_bucket_name = '启用对象存储时必须填写 Bucket 名称'
    if (!values.oss_endpoint.trim()) errors.oss_endpoint = '启用对象存储时必须填写 Endpoint'
  }

  return errors
}

const fieldConfig = [
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

const SystemSettings = () => {
  const [values, setValues] = useState(defaultValues)
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const { handleBusinessError, handleError, showSuccess } = useErrorHandler()

  const provider = values.provider || 'local'

  const fetchStorageSettings = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.systemSettings.getStorageSettings()
      const data = response.data || {}
      setValues({
        provider: data.provider || 'local',
        local_upload_dir: data.local_upload_dir || 'uploads',
        local_full_url: data.local_full_url || '',
        oss_access_key_id: data.oss_access_key_id || '',
        oss_access_key_secret: data.oss_access_key_secret || '',
        oss_bucket_name: data.oss_bucket_name || '',
        oss_endpoint: data.oss_endpoint || '',
        oss_bucket_domain: data.oss_bucket_domain || '',
        oss_upload_dir: data.oss_upload_dir || 'uploads',
      })
    } catch (error) {
      handleError(error, '获取系统设置失败')
    } finally {
      setLoading(false)
    }
  }, [handleError])

  useEffect(() => {
    void fetchStorageSettings()
  }, [fetchStorageSettings])

  const updateField = (field, value) => {
    setValues((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
  }

  const handleSave = async (event) => {
    event.preventDefault()

    const nextErrors = validateSettings(values)
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors)
      return
    }

    setSaving(true)
    try {
      const payload = {
        ...values,
        provider,
      }
      const response = await api.systemSettings.updateStorageSettings(payload)
      const data = response.data || payload

      setValues({
        provider: data.provider || 'local',
        local_upload_dir: data.local_upload_dir || 'uploads',
        local_full_url: data.local_full_url || '',
        oss_access_key_id: data.oss_access_key_id || '',
        oss_access_key_secret: data.oss_access_key_secret || '',
        oss_bucket_name: data.oss_bucket_name || '',
        oss_endpoint: data.oss_endpoint || '',
        oss_bucket_domain: data.oss_bucket_domain || '',
        oss_upload_dir: data.oss_upload_dir || 'uploads',
      })
      showSuccess('存储设置已保存')
    } catch (error) {
      handleBusinessError(error, '保存系统设置失败')
    } finally {
      setSaving(false)
    }
  }

  const statusBadges = useMemo(
    () => [
      {
        label: '当前模式',
        value: provider === 'oss' ? '对象存储' : '本地存储',
      },
      {
        label: '本地目录',
        value: values.local_upload_dir || 'uploads',
      },
      {
        label: '对象存储目录',
        value: values.oss_upload_dir || 'uploads',
      },
    ],
    [provider, values.local_upload_dir, values.oss_upload_dir],
  )

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-3 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">系统设置</h1>
          <p className="text-sm text-muted-foreground">管理系统级配置，当前开放存储设置</p>
        </div>

        <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
          {statusBadges.map((item) => (
            <div key={item.label} className="rounded-lg border bg-background px-3 py-2">
              <span className="mr-2 text-muted-foreground">{item.label}</span>
              <span className="font-medium text-foreground">{item.value}</span>
            </div>
          ))}
        </div>
      </section>

      <Tabs defaultValue="storage">
        <TabsList>
          <TabsTrigger value="storage">存储设置</TabsTrigger>
        </TabsList>

        <TabsContent value="storage">
          <Card>
            <CardHeader>
              <CardTitle>存储设置</CardTitle>
              <CardDescription>切换存储模式后保存即可生效，不影响另一套配置的填写</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-sm text-muted-foreground">加载中...</div>
              ) : (
                <form className="flex flex-col gap-6" onSubmit={handleSave}>
                  <div className="flex flex-col gap-4 rounded-lg border bg-muted/20 p-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-start gap-3">
                      <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                        <ServerCogIcon />
                      </div>
                      <div>
                        <div className="text-sm font-medium">当前生效模式</div>
                        <div className="text-sm text-muted-foreground">
                          当前为 {provider === 'oss' ? '对象存储' : '本地存储'}，切换后保存即可应用
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-muted-foreground">本地</span>
                      <Switch
                        checked={provider === 'oss'}
                        onCheckedChange={(checked) => updateField('provider', checked ? 'oss' : 'local')}
                      />
                      <span className="text-sm text-muted-foreground">对象存储</span>
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <Card size="sm">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <FolderIcon className="size-4" />
                          本地存储
                        </CardTitle>
                        <CardDescription>本地磁盘目录与访问地址</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <FieldGroup>
                          {fieldConfig.map((field) => (
                            <Field key={field.key} data-invalid={Boolean(errors[field.key])}>
                              <FieldLabel htmlFor={field.key} required={field.key === 'local_upload_dir'}>
                                {field.label}
                              </FieldLabel>
                              <Input
                                id={field.key}
                                required={field.key === 'local_upload_dir'}
                                value={values[field.key]}
                                placeholder={field.placeholder}
                                onChange={(event) => updateField(field.key, event.target.value)}
                                aria-invalid={Boolean(errors[field.key])}
                              />
                              <FieldError>{errors[field.key]}</FieldError>
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
                        <CardDescription>启用对象存储时必须完成以下配置</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <FieldGroup className="grid gap-4 md:grid-cols-2">
                          {ossFieldConfig.map((field) => (
                            <Field
                              key={field.key}
                              data-disabled={provider !== 'oss'}
                              data-invalid={Boolean(errors[field.key])}
                              className={field.key === 'oss_bucket_domain' ? 'md:col-span-2' : undefined}
                            >
                              <FieldLabel
                                htmlFor={field.key}
                                required={
                                  field.key === 'oss_upload_dir' ||
                                  (provider === 'oss' &&
                                    ['oss_access_key_id', 'oss_access_key_secret', 'oss_bucket_name', 'oss_endpoint'].includes(field.key))
                                }
                              >
                                {field.label}
                              </FieldLabel>
                              <Input
                                id={field.key}
                                type={field.type || 'text'}
                                required={
                                  field.key === 'oss_upload_dir' ||
                                  (provider === 'oss' &&
                                    ['oss_access_key_id', 'oss_access_key_secret', 'oss_bucket_name', 'oss_endpoint'].includes(field.key))
                                }
                                disabled={provider !== 'oss'}
                                value={values[field.key]}
                                placeholder={field.placeholder}
                                onChange={(event) => updateField(field.key, event.target.value)}
                                aria-invalid={Boolean(errors[field.key])}
                              />
                              <FieldError>{errors[field.key]}</FieldError>
                            </Field>
                          ))}
                        </FieldGroup>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={saving}>
                      <SaveIcon data-icon="inline-start" />
                      {saving ? '保存中...' : '保存设置'}
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
