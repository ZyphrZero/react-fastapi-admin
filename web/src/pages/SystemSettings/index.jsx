import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Row,
  Switch,
  Tabs,
} from 'antd'
import {
  CloudServerOutlined,
  DatabaseOutlined,
  FolderOpenOutlined,
  SaveOutlined,
} from '@ant-design/icons'

import api from '@/api'
import { useErrorHandler } from '@/hooks/useErrorHandler'

const SystemSettings = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const provider = Form.useWatch('provider', form) || 'local'

  const { handleBusinessError, handleError, showSuccess } = useErrorHandler()

  const fetchStorageSettings = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.systemSettings.getStorageSettings()
      const data = response.data || {}
      form.setFieldsValue({
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
  }, [form, handleError])

  useEffect(() => {
    void fetchStorageSettings()
  }, [fetchStorageSettings])

  const handleSave = async (values) => {
    setSaving(true)
    try {
      const payload = {
        ...values,
        provider: values.provider || 'local',
      }
      const response = await api.systemSettings.updateStorageSettings(payload)
      const data = response.data || payload
      form.setFieldsValue({
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

  const storageSettingsContent = (
    <Form
      form={form}
      layout="vertical"
      initialValues={{
        provider: 'local',
        local_upload_dir: 'uploads',
        local_full_url: '',
        oss_upload_dir: 'uploads',
      }}
      onFinish={handleSave}
    >
      <Form.Item name="provider" hidden>
        <Input />
      </Form.Item>

      <div className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-4 mb-6">
        <div>
          <div className="text-base font-semibold text-gray-800">当前生效模式</div>
          <div className="text-sm text-gray-500 mt-1">切换后保存即可生效，不影响另一套配置的填写和保存。</div>
        </div>
        <Switch
          checked={provider === 'oss'}
          checkedChildren="对象存储"
          unCheckedChildren="本地"
          onChange={(checked) => {
            form.setFieldValue('provider', checked ? 'oss' : 'local')
          }}
        />
      </div>

      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <FolderOpenOutlined className="text-gray-500" />
          <h2 className="text-base font-semibold text-gray-800 mb-0">本地存储</h2>
        </div>

        <Row gutter={[16, 0]}>
          <Col xs={24} md={12}>
            <Form.Item
              label="本地上传目录"
              name="local_upload_dir"
              rules={[{ required: true, message: '请填写本地上传目录' }]}
            >
              <Input
                size="large"
                prefix={<FolderOpenOutlined className="text-slate-400" />}
                placeholder="例如 uploads"
              />
            </Form.Item>
          </Col>
          <Col xs={24} md={12}>
            <Form.Item label="本地完整访问地址" name="local_full_url">
              <Input
                size="large"
                prefix={<CloudServerOutlined className="text-slate-400" />}
                placeholder="可选，例如 https://files.example.com"
              />
            </Form.Item>
          </Col>
        </Row>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <CloudServerOutlined className="text-gray-500" />
        <h2 className="text-base font-semibold text-gray-800 mb-0">对象存储</h2>
      </div>

      <Row gutter={[16, 0]}>
        <Col xs={24} md={12}>
          <Form.Item
            label="AccessKey ID"
            name="oss_access_key_id"
            rules={[
              {
                required: provider === 'oss',
                message: '启用对象存储时必须填写 AccessKey ID',
              },
            ]}
          >
            <Input
              size="large"
              prefix={<CloudServerOutlined className="text-slate-400" />}
              placeholder="请输入 AccessKey ID"
              disabled={provider !== 'oss'}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item
            label="AccessKey Secret"
            name="oss_access_key_secret"
            rules={[
              {
                required: provider === 'oss',
                message: '启用对象存储时必须填写 AccessKey Secret',
              },
            ]}
          >
            <Input.Password
              size="large"
              prefix={<DatabaseOutlined className="text-slate-400" />}
              placeholder="请输入 AccessKey Secret"
              disabled={provider !== 'oss'}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item
            label="Bucket 名称"
            name="oss_bucket_name"
            rules={[
              {
                required: provider === 'oss',
                message: '启用对象存储时必须填写 Bucket 名称',
              },
            ]}
          >
            <Input
              size="large"
              prefix={<DatabaseOutlined className="text-slate-400" />}
              placeholder="例如 media-assets"
              disabled={provider !== 'oss'}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item
            label="Endpoint"
            name="oss_endpoint"
            rules={[
              {
                required: provider === 'oss',
                message: '启用对象存储时必须填写 Endpoint',
              },
            ]}
          >
            <Input
              size="large"
              prefix={<CloudServerOutlined className="text-slate-400" />}
              placeholder="例如 oss-cn-hangzhou.aliyuncs.com"
              disabled={provider !== 'oss'}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item label="自定义域名" name="oss_bucket_domain">
            <Input
              size="large"
              prefix={<CloudServerOutlined className="text-slate-400" />}
              placeholder="可选，例如 cdn.example.com"
              disabled={provider !== 'oss'}
            />
          </Form.Item>
        </Col>
        <Col xs={24} md={12}>
          <Form.Item
            label="上传目录"
            name="oss_upload_dir"
            rules={[{ required: true, message: '请填写上传目录' }]}
          >
            <Input
              size="large"
              prefix={<FolderOpenOutlined className="text-slate-400" />}
              placeholder="例如 uploads"
              disabled={provider !== 'oss'}
            />
          </Form.Item>
        </Col>
      </Row>

      <div className="flex justify-end">
        <Button type="primary" htmlType="submit" size="large" icon={<SaveOutlined />} loading={saving}>
          保存设置
        </Button>
      </div>
    </Form>
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">系统设置</h1>
        <p className="text-gray-500 mt-1">管理系统级配置，仅超级管理员可修改。当前开放存储设置。</p>
      </div>

      <Card loading={loading} title="设置项">
        <Tabs
          defaultActiveKey="storage"
          items={[
            {
              key: 'storage',
              label: '存储设置',
              children: storageSettingsContent,
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default SystemSettings
