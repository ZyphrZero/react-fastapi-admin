import { useMemo, useState } from 'react'
import { ArrowRightIcon, LockKeyholeIcon, SparklesIcon, UserIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import api from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
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

const validateLoginForm = (values) => {
  const nextErrors = {}

  if (!values.username.trim()) {
    nextErrors.username = '请输入用户名'
  } else if (values.username.trim().length < 3) {
    nextErrors.username = '用户名至少 3 个字符'
  }

  if (!values.password) {
    nextErrors.password = '请输入密码'
  }

  return nextErrors
}

const Login = () => {
  const [loading, setLoading] = useState(false)
  const [formValues, setFormValues] = useState({ username: '', password: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const navigate = useNavigate()
  const { handleBusinessError, showSuccess } = useErrorHandler()

  const formIsValid = useMemo(() => Object.keys(validateLoginForm(formValues)).length === 0, [formValues])

  const updateField = (name, value) => {
    setFormValues((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: undefined }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    const nextErrors = validateLoginForm(formValues)
    if (Object.keys(nextErrors).length > 0) {
      setFieldErrors(nextErrors)
      return
    }

    setLoading(true)
    try {
      const response = await api.auth.login({
        username: formValues.username.trim(),
        password: formValues.password,
      })

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

      showSuccess('登录成功')
      navigate(findFirstAccessiblePath(userMenu.data || []))
    } catch (error) {
      clearSession()
      handleBusinessError(error, '登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-muted p-6 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <div className="flex items-center gap-2 self-center font-medium">
          <div className="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <SparklesIcon className="size-4" />
          </div>
          React FastAPI Admin
        </div>

        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-xl">登录后台</CardTitle>
            <CardDescription>使用账户信息继续</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit}>
              <FieldGroup>
                <Field data-invalid={Boolean(fieldErrors.username)}>
                  <FieldLabel htmlFor="username" required>用户名</FieldLabel>
                  <div className="relative">
                    <UserIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="username"
                      autoComplete="username"
                      required
                      className="pl-9"
                      placeholder="请输入用户名"
                      value={formValues.username}
                      onChange={(event) => updateField('username', event.target.value)}
                      aria-invalid={Boolean(fieldErrors.username)}
                    />
                  </div>
                  <FieldError>{fieldErrors.username}</FieldError>
                </Field>

                <Field data-invalid={Boolean(fieldErrors.password)}>
                  <FieldLabel htmlFor="password" required>密码</FieldLabel>
                  <div className="relative">
                    <LockKeyholeIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="password"
                      type="password"
                      required
                      autoComplete="current-password"
                      className="pl-9"
                      placeholder="请输入密码"
                      value={formValues.password}
                      onChange={(event) => updateField('password', event.target.value)}
                      aria-invalid={Boolean(fieldErrors.password)}
                    />
                  </div>
                  <FieldError>{fieldErrors.password}</FieldError>
                </Field>

                <Field>
                  <Button type="submit" size="lg" disabled={loading || !formIsValid}>
                    {loading ? '登录中...' : '登录后台'}
                    {!loading ? <ArrowRightIcon data-icon="inline-end" /> : null}
                  </Button>
                </Field>
              </FieldGroup>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default Login
