import { useState } from 'react'
import { Form, Input, Button, Card } from 'antd'
import { UserOutlined, LockOutlined, LoginOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import api from '@/api'
import { useErrorHandler } from '@/hooks/useErrorHandler'
import { findFirstAccessiblePath } from '@/utils/permission'
import {
  clearSession,
  setAccessToken,
  setRefreshToken,
  setStoredApiPermissions,
  setStoredMenus,
  setStoredUserInfo,
} from '@/utils/session'

const Login = () => {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { handleBusinessError, showSuccess } = useErrorHandler()

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const response = await api.auth.login({
        username: values.username,
        password: values.password,
      })

      // 保存token和用户信息
      setAccessToken(response.data.access_token)
      setRefreshToken(response.data.refresh_token)
      
      const [userInfo, userMenu, userApi] = await Promise.all([
        api.auth.getUserInfo(),
        api.auth.getUserMenu(),
        api.auth.getUserApi(),
      ])

      setStoredUserInfo(userInfo.data)
      setStoredMenus(userMenu.data || [])
      setStoredApiPermissions(userApi.data || [])

      showSuccess('登录成功！')
      navigate(findFirstAccessiblePath(userMenu.data || []))
    } catch (error) {
      clearSession()
      handleBusinessError(error, '登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-gradient-to-br from-blue-400/20 to-purple-400/20 blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-gradient-to-br from-purple-400/20 to-pink-400/20 blur-3xl"></div>
      </div>

      <div className="relative w-full max-w-md">
        <Card 
          className="shadow-2xl border-0 backdrop-blur-sm bg-white/90"
          styles={{
            body: {
              padding: '2rem'
            }
          }}
        >
          {/* Logo和标题 */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mx-auto mb-4 flex items-center justify-center">
              <LoginOutlined className="text-2xl text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">React FastAPI Admin</h1>
            <p className="text-gray-500">欢迎回来，请登录您的账户</p>
          </div>

          {/* 登录表单 */}
          <Form
            name="login"
            onFinish={onFinish}
            size="large"
            className="space-y-4"
          >
            <Form.Item
              name="username"
              rules={[
                { required: true, message: '请输入用户名!' },
                { min: 3, message: '用户名至少3个字符!' }
              ]}
            >
              <Input
                prefix={<UserOutlined className="text-gray-400" />}
                placeholder="用户名"
                className="rounded-lg border-gray-200 hover:border-blue-400 focus:border-blue-500"
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码!' }
              ]}
            >
              <Input.Password
                prefix={<LockOutlined className="text-gray-400" />}
                placeholder="密码"
                className="rounded-lg border-gray-200 hover:border-blue-400 focus:border-blue-500"
                autoComplete="current-password"
              />
            </Form.Item>

            <Form.Item className="mb-0">
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                className="w-full h-12 rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 border-0 hover:from-blue-600 hover:to-purple-700 shadow-lg hover:shadow-xl transition-all duration-300"
              >
                {loading ? '登录中...' : '登录'}
              </Button>
            </Form.Item>
          </Form>

        </Card>

        {/* 版权信息 */}
        <div className="text-center mt-8 text-sm text-gray-400">
          <p>© 2025 React FastAPI Admin. 基于 React + Ant Design + Tailwind CSS</p>
        </div>
      </div>
    </div>
  )
}

export default Login 
