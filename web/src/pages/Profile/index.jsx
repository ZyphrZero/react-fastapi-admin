import { useCallback, useEffect, useState } from 'react'
import { Row, Col, Card, Form, Input, Button, Tabs, Avatar, Divider } from 'antd'
import { UserOutlined, LockOutlined, EditOutlined, SaveOutlined, MailOutlined, SafetyOutlined, PhoneOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '@/api'
import { useErrorHandler } from '@/hooks/useErrorHandler'
import PasswordStrengthIndicator from '@/components/PasswordStrengthIndicator'
import { clearSession, setStoredUserInfo } from '@/utils/session'

const Profile = () => {
  const [userInfo, setUserInfo] = useState({})
  const [loading, setLoading] = useState(false)
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordStrength, setPasswordStrength] = useState(null)
  const [profileForm] = Form.useForm()
  const [passwordForm] = Form.useForm()
  const navigate = useNavigate()
  const { handleError, handleBusinessError, showSuccess, showWarning, message } = useErrorHandler()

  // 获取用户信息
  const fetchUserInfo = useCallback(async () => {
    try {
      const response = await api.auth.getUserInfo()
      setUserInfo(response.data)
      // 设置表单初始值，确保空值显示为空字符串
      profileForm.setFieldsValue({
        nickname: response.data.nickname || '',
        email: response.data.email || '',
        phone: response.data.phone || '',
      })
    } catch (error) {
      // 获取用户信息失败时使用通用错误处理
      handleError(error, '获取用户信息失败')
    }
  }, [handleError, profileForm])

  useEffect(() => {
    void fetchUserInfo()
  }, [fetchUserInfo])

  // 更新个人信息
  const handleUpdateProfile = async (values) => {
    setLoading(true)
    try {
      // 处理空值，当字段为空时删除该字段，避免后端验证错误
      const processedValues = { ...values }
      
      // 清理字段值
      if (values.email !== undefined) {
        processedValues.email = values.email?.trim() || undefined
      }
      if (values.phone !== undefined) {
        processedValues.phone = values.phone?.trim() || undefined
      }
      if (values.nickname !== undefined) {
        processedValues.nickname = values.nickname?.trim() || undefined
      }
      
      await api.auth.updateProfile(processedValues)
      showSuccess('个人信息更新成功！')
      
      // 重新获取用户信息并同步到会话状态
      const response = await api.auth.getUserInfo()
      setUserInfo(response.data)
      setStoredUserInfo(response.data)
      
      // 更新表单值以反映最新的用户信息
      profileForm.setFieldsValue({
        nickname: response.data.nickname || '',
        email: response.data.email || '',
        phone: response.data.phone || '',
      })
    } catch (error) {
      // 个人信息更新失败时使用业务错误处理
      handleBusinessError(error, '更新失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  // 修改密码
  const handleUpdatePassword = async (values) => {
    // 检查密码强度
    if (passwordStrength && passwordStrength.score < 2) {
      showWarning('密码强度太弱，请设置更强的密码')
      return
    }

    setPasswordLoading(true)
    try {
      await api.auth.updatePassword({
        old_password: values.oldPassword,
        new_password: values.newPassword,
      })
      showSuccess('密码修改成功！为了安全起见，请重新登录。')
      passwordForm.resetFields()
      setPasswordStrength(null) // 重置密码强度状态

      // 清除登录信息并跳转到登录页
      setTimeout(() => {
        clearSession()
        navigate('/login')
      }, 1500) // 1.5秒后跳转，让用户看到成功提示

    } catch (error) {
      // 密码修改失败时使用业务错误处理，并支持自定义处理
      handleBusinessError(error, '密码修改失败，请重试', (standardError) => {
        // 自定义处理：如果是旧密码错误，可以提供更具体的提示
        if (standardError.message.includes('旧密码') || standardError.message.includes('密码验证')) {
          showWarning('当前密码输入错误，请重新输入')
        } else {
          message.error(standardError.message)
        }
        return standardError
      })
    } finally {
      setPasswordLoading(false)
    }
  }

  // 格式化日期
  const formatDate = (dateString) => {
    if (!dateString) return '暂无数据'
    return new Date(dateString).toLocaleString('zh-CN')
  }

  return (
    <div className="space-y-6">
      {/* 欢迎标题 */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
        <div className="flex items-center space-x-4">
          <Avatar 
            size={64} 
            icon={<UserOutlined />} 
            className="bg-white/20 border-2 border-white/30"
          />
          <div>
            <h1 className="text-2xl font-bold mb-1">个人中心</h1>
            <p className="opacity-90">管理您的个人信息和账户设置</p>
          </div>
        </div>
      </div>

      {/* 账户统计信息 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable className="h-full">
            <div className="flex flex-col justify-center h-full py-4">
              <div className="text-gray-500 text-sm mb-2">显示名称</div>
              <div className="flex items-center">
                <UserOutlined className="text-blue-500 text-lg mr-2" />
                <span className="text-gray-800 font-bold text-base">
                  {userInfo.nickname || userInfo.username || '未设置'}
                </span>
              </div>
                              <div className="text-xs text-gray-500 mt-2">
                用户名: @{userInfo.username || '未设置'}
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable className="h-full">
            <div className="flex flex-col justify-center h-full py-4">
              <div className="text-gray-500 text-sm mb-2">邮箱地址</div>
              <div className="flex items-center">
                <MailOutlined className="text-green-500 text-lg mr-2" />
                <span className="text-gray-800 font-bold text-base">
                  {userInfo.email || '未设置'}
                </span>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable className="h-full">
            <div className="flex flex-col justify-center h-full py-4">
              <div className="text-gray-500 text-sm mb-2">手机号码</div>
              <div className="flex items-center">
                <PhoneOutlined className="text-orange-500 text-lg mr-2" />
                <span className="text-gray-800 font-bold text-base">
                  {userInfo.phone || '未设置'}
                </span>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable className="h-full">
            <div className="flex flex-col justify-center h-full py-4">
              <div className="text-gray-500 text-sm mb-2">账户状态</div>
              <div className="flex items-center">
                <SafetyOutlined className="text-purple-500 text-lg mr-2" />
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    userInfo.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {userInfo.is_active ? '正常' : '禁用'}
                  </span>
                  {userInfo.is_superuser && (
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      管理员
                    </span>
                  )}
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 账户详情和操作 */}
      <Row gutter={[16, 16]}>
        {/* 账户详细信息 */}
        <Col xs={24} lg={8}>
          <Card title="账户详情" hoverable className="h-full">
            <div className="space-y-4">
              <div className="text-center pb-4 border-b border-gray-100">
                <Avatar 
                  size={80} 
                  icon={<UserOutlined />} 
                  className="bg-gradient-to-r from-blue-500 to-purple-600 mb-3"
                />
                <h3 className="text-lg font-semibold text-gray-800">
                  {userInfo.nickname || userInfo.username || '未设置'}
                </h3>
                <p className="text-gray-500 text-sm flex items-center">
                  <UserOutlined className="mr-1" />
                  @{userInfo.username || '未设置'}
                </p>
                <p className="text-gray-500 text-sm flex items-center">
                  <MailOutlined className="mr-1" />
                  {userInfo.email || '未设置'}
                </p>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 flex items-center">
                    <PhoneOutlined className="mr-2 text-orange-500" />
                    手机号码：
                  </span>
                  <span className="text-sm font-medium">{userInfo.phone || '未设置'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 flex items-center">
                    <MailOutlined className="mr-2 text-green-500" />
                    邮箱地址：
                  </span>
                  <span className="text-sm font-medium">{userInfo.email || '未设置'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">创建时间：</span>
                  <span className="text-sm">{formatDate(userInfo.created_at)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">更新时间：</span>
                  <span className="text-sm">{formatDate(userInfo.updated_at)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">最后登录：</span>
                  <span className="text-sm">{formatDate(userInfo.last_login)}</span>
                </div>
              </div>
            </div>
          </Card>
        </Col>

        {/* 操作选项卡 */}
        <Col xs={24} lg={16}>
          <Card hoverable className="h-full">
            <Tabs 
              defaultActiveKey="profile" 
              size="large"
              items={[
                {
                  key: 'profile',
                  label: (
                    <span>
                      <EditOutlined />
                      修改信息
                    </span>
                  ),
                  children: (
                    <div className="max-w-lg">
                      <Form
                        form={profileForm}
                        layout="vertical"
                        onFinish={handleUpdateProfile}
                        className="space-y-4"
                      >
                        <Form.Item
                          label="用户名"
                        >
                          <Input
                            prefix={<UserOutlined className="text-gray-400" />}
                            value={userInfo.username}
                            size="large"
                            disabled
                            className="bg-gray-50"
                            placeholder="用户名(不可修改)"
                            autoComplete="username"
                          />
                        </Form.Item>

                        <Form.Item
                          label="昵称"
                          name="nickname"
                          rules={[
                            { max: 30, message: '昵称不能超过30个字符!' }
                          ]}
                        >
                          <Input
                            prefix={<UserOutlined className="text-gray-400" />}
                            placeholder="请输入昵称"
                            size="large"
                            autoComplete="nickname"
                          />
                        </Form.Item>

                        <Form.Item
                          label="邮箱地址"
                          name="email"
                          rules={[
                            { type: 'email', message: '请输入有效的邮箱地址!' }
                          ]}
                        >
                          <Input
                            prefix={<MailOutlined className="text-gray-400" />}
                            placeholder="请输入邮箱地址"
                            size="large"
                            autoComplete="email"
                          />
                        </Form.Item>

                        <Form.Item
                          label="手机号码"
                          name="phone"
                          rules={[
                            { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的11位手机号码!' },
                            { len: 11, message: '手机号码必须是11位数字!' }
                          ]}
                        >
                          <Input
                            prefix={<PhoneOutlined className="text-gray-400" />}
                            placeholder="请输入11位手机号码"
                            size="large"
                            maxLength={11}
                            autoComplete="tel"
                            onInput={(e) => {
                              // 只允许输入数字
                              e.target.value = e.target.value.replace(/[^\d]/g, '')
                            }}
                          />
                        </Form.Item>

                        <Form.Item className="mb-0">
                          <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                            icon={<SaveOutlined />}
                            size="large"
                            className="bg-gradient-to-r from-blue-500 to-purple-600 border-0 hover:from-blue-600 hover:to-purple-700"
                          >
                            {loading ? '保存中...' : '保存更改'}
                          </Button>
                        </Form.Item>
                      </Form>
                    </div>
                  )
                },
                {
                  key: 'password',
                  label: (
                    <span>
                      <LockOutlined />
                      修改密码
                    </span>
                  ),
                  children: (
                    <div className="max-w-lg">
                      <Form
                        form={passwordForm}
                        layout="vertical"
                        onFinish={handleUpdatePassword}
                        className="space-y-4"
                      >
                        <Form.Item
                          label="当前密码"
                          name="oldPassword"
                          rules={[
                            { required: true, message: '请输入当前密码!' }
                          ]}
                        >
                          <Input.Password
                            prefix={<LockOutlined className="text-gray-400" />}
                            placeholder="请输入当前密码"
                            size="large"
                            autoComplete="current-password"
                          />
                        </Form.Item>

                        <Form.Item
                          label="新密码"
                          name="newPassword"
                          rules={[
                            { required: true, message: '请输入新密码!' },
                            () => ({
                              validator(_, value) {
                                if (!value) return Promise.resolve()
                                
                                // 检查密码长度
                                if (value.length < 8) {
                                  return Promise.reject(new Error('密码长度不能少于8个字符'))
                                }
                                
                                // 检查大写字母
                                if (!/[A-Z]/.test(value)) {
                                  return Promise.reject(new Error('密码必须包含至少一个大写字母'))
                                }
                                
                                // 检查小写字母
                                if (!/[a-z]/.test(value)) {
                                  return Promise.reject(new Error('密码必须包含至少一个小写字母'))
                                }
                                
                                // 检查数字
                                if (!/\d/.test(value)) {
                                  return Promise.reject(new Error('密码必须包含至少一个数字'))
                                }
                                
                                // 检查特殊字符
                                if (!/[!@#$%^&*(),.?":{}|<>]/.test(value)) {
                                  return Promise.reject(new Error('密码必须包含至少一个特殊字符'))
                                }
                                
                                return Promise.resolve()
                              }
                            })
                          ]}
                        >
                          <Input.Password
                            prefix={<LockOutlined className="text-gray-400" />}
                            placeholder="请输入新密码"
                            size="large"
                            autoComplete="new-password"
                          />
                        </Form.Item>

                        <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.newPassword !== currentValues.newPassword}>
                          {({ getFieldValue }) => (
                            <PasswordStrengthIndicator 
                              password={getFieldValue('newPassword')}
                              onStrengthChange={setPasswordStrength}
                              showSuggestions={true}
                            />
                          )}
                        </Form.Item>

                        <Form.Item
                          label="确认新密码"
                          name="confirmPassword"
                          dependencies={['newPassword']}
                          rules={[
                            { required: true, message: '请确认新密码!' },
                            ({ getFieldValue }) => ({
                              validator(_, value) {
                                if (!value || getFieldValue('newPassword') === value) {
                                  return Promise.resolve()
                                }
                                return Promise.reject(new Error('两次输入的密码不一致!'))
                              },
                            }),
                          ]}
                        >
                          <Input.Password
                            prefix={<LockOutlined className="text-gray-400" />}
                            placeholder="请确认新密码"
                            size="large"
                            autoComplete="new-password"
                          />
                        </Form.Item>

                        <Form.Item className="mb-0">
                          <Button
                            type="primary"
                            htmlType="submit"
                            loading={passwordLoading}
                            icon={<SaveOutlined />}
                            size="large"
                            className="bg-gradient-to-r from-blue-500 to-purple-600 border-0 hover:from-blue-600 hover:to-purple-700"
                          >
                            {passwordLoading ? '修改中...' : '修改密码'}
                          </Button>
                        </Form.Item>
                      </Form>

                      <Divider />
                      
                      <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                        <h4 className="text-sm font-medium text-orange-800 mb-2 flex items-center">
                          <SafetyOutlined className="mr-2" />
                          密码安全提示
                        </h4>
                        <ul className="text-xs text-orange-700 space-y-1">
                          <li>• 密码长度至少8个字符</li>
                          <li>• 必须包含大写字母、小写字母、数字和特殊字符</li>
                          <li>• 建议使用强度指示器确保密码安全</li>
                          <li>• 定期更换密码以确保账户安全</li>
                          <li>• 不要使用容易猜测的密码</li>
                        </ul>
                      </div>
                    </div>
                  )
                }
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Profile 
