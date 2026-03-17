import { useMemo, useState } from 'react'
import { ArrowRightIcon, LockKeyholeIcon, ShieldCheckIcon, UserIcon, WaypointsIcon, WebhookIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import api from '@/api'
import BrandLogo from '@/components/BrandLogo'
import { ModeToggle } from '@/components/mode-toggle'
import { useTheme } from '@/components/theme-provider'
import { Badge } from '@/components/ui/badge'
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
  const { resolvedTheme } = useTheme()
  const { handleBusinessError, showSuccess } = useErrorHandler()

  const formIsValid = useMemo(() => Object.keys(validateLoginForm(formValues)).length === 0, [formValues])
  const loginBackgroundStyle = useMemo(
    () =>
      resolvedTheme === 'dark'
        ? {
            backgroundColor: 'rgb(10 14 24)',
            backgroundImage:
              'radial-gradient(rgb(251 114 153 / 0.14) 1px, transparent 1px), linear-gradient(145deg, rgb(8 11 19) 0%, rgb(15 23 42) 52%, rgb(7 13 24) 100%)',
            backgroundSize: '10px 10px, cover',
            backgroundPosition: '0 0, center',
          }
        : {
            backgroundColor: 'rgb(255 249 251)',
            backgroundImage:
              'radial-gradient(rgb(251 114 153 / 0.24) 1px, transparent 1px), linear-gradient(145deg, rgb(255 248 250) 0%, rgb(255 255 255) 48%, rgb(248 250 252) 100%)',
            backgroundSize: '10px 10px, cover',
            backgroundPosition: '0 0, center',
          },
    [resolvedTheme],
  )
  const featureItems = [
    {
      title: '审计留痕',
      description: '关键操作自动沉淀审计轨迹，方便追踪与回放。',
      icon: ShieldCheckIcon,
    },
    {
      title: '接口治理',
      description: 'API 目录与权限体系联动，减少维护偏差。',
      icon: WebhookIcon,
    },
    {
      title: '趋势洞察',
      description: '工作台汇总趋势、分布与运行状态，快速判断健康度。',
      icon: WaypointsIcon,
    },
  ]

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
    <div
      className="relative flex min-h-svh flex-col overflow-hidden"
      style={loginBackgroundStyle}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.82),transparent_48%)] dark:bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.06),transparent_42%)]" />
      <div className="pointer-events-none absolute -top-20 left-1/2 size-80 -translate-x-1/2 rounded-full bg-rose-300/25 blur-3xl dark:bg-rose-500/10" />
      <div className="pointer-events-none absolute right-10 bottom-10 size-56 rounded-full bg-sky-200/20 blur-3xl dark:bg-cyan-400/10" />
      <div className="pointer-events-none absolute left-[12%] bottom-[12%] size-52 rounded-full bg-amber-200/15 blur-3xl dark:bg-indigo-500/10" />

      <div className="absolute top-6 right-6 z-20">
        <ModeToggle className="border-white/60 bg-background/70 shadow-sm backdrop-blur dark:border-white/10 dark:bg-background/50" />
      </div>

      <div className="relative z-10 flex flex-1 items-center justify-center p-6 md:p-10">
        <div className="grid w-full max-w-6xl gap-8 lg:grid-cols-[1.08fr_0.92fr] lg:items-stretch">
          <section className="hidden lg:block">
            <div className="relative flex h-full flex-col justify-between overflow-hidden rounded-[2rem] border border-white/65 bg-white/55 p-8 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur-xl dark:border-white/10 dark:bg-white/6 dark:shadow-[0_28px_90px_rgba(2,8,23,0.42)]">
              <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.5),transparent_52%)] dark:bg-[linear-gradient(135deg,rgba(255,255,255,0.08),transparent_52%)]" />
              <div className="relative z-10 flex flex-col gap-8">
                <BrandLogo markClassName="size-14" title="React FastAPI Admin" subtitle="CONTROL CENTER" />

                <div className="max-w-xl space-y-4">
                  <Badge variant="outline" className="rounded-full border-rose-300/50 bg-white/55 px-3 py-1 text-rose-700 dark:border-rose-400/20 dark:bg-white/8 dark:text-rose-200">
                    点阵背景 · 渐变控制台
                  </Badge>
                  <h1 className="text-4xl font-semibold tracking-[-0.04em] text-foreground">
                    更像产品入口，而不是一张普通的登录表单。
                  </h1>
                  <p className="max-w-lg text-sm leading-7 text-muted-foreground">
                    这套后台把权限、审计、接口目录和运行概览统一到一块控制台里。登录只是入口，
                    风格也应该和整站的品牌语言保持一致。
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  {featureItems.map((item) => {
                    const FeatureIcon = item.icon

                    return (
                      <div
                        key={item.title}
                        className="rounded-2xl border border-white/55 bg-background/65 p-4 backdrop-blur-sm dark:border-white/8 dark:bg-background/35"
                      >
                        <div className="flex size-10 items-center justify-center rounded-2xl bg-foreground/[0.06] text-foreground dark:bg-white/10">
                          <FeatureIcon />
                        </div>
                        <div className="mt-4 text-sm font-medium text-foreground">{item.title}</div>
                        <p className="mt-2 text-xs leading-6 text-muted-foreground">{item.description}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </section>

          <section className="flex items-center justify-center">
            <div className="w-full max-w-md">
              <div className="mb-6 flex justify-center lg:hidden">
                <BrandLogo title="React FastAPI Admin" subtitle="CONTROL CENTER" />
              </div>

              <Card className="relative overflow-hidden border-white/65 bg-background/84 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur-xl dark:border-white/10 dark:bg-background/74 dark:shadow-[0_28px_90px_rgba(2,8,23,0.46)]">
                <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-[linear-gradient(180deg,rgba(251,113,133,0.08),transparent)] dark:bg-[linear-gradient(180deg,rgba(251,113,133,0.10),transparent)]" />
                <CardHeader className="relative text-center">
                  <div className="mb-2 flex justify-center">
                    <Badge variant="outline" className="rounded-full bg-background/70 px-3 py-1 text-xs backdrop-blur dark:bg-background/40">
                      Secure Access Portal
                    </Badge>
                  </div>
                  <CardTitle className="text-2xl tracking-[-0.03em]">登录后台</CardTitle>
                  <CardDescription>使用账户信息继续进入控制台</CardDescription>
                </CardHeader>
                <CardContent className="relative">
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
                            className="border-white/50 bg-background/78 pl-9 dark:border-white/10 dark:bg-background/45"
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
                            className="border-white/50 bg-background/78 pl-9 dark:border-white/10 dark:bg-background/45"
                            placeholder="请输入密码"
                            value={formValues.password}
                            onChange={(event) => updateField('password', event.target.value)}
                            aria-invalid={Boolean(fieldErrors.password)}
                          />
                        </div>
                        <FieldError>{fieldErrors.password}</FieldError>
                      </Field>

                      <Field>
                        <Button type="submit" size="lg" disabled={loading || !formIsValid} className="shadow-lg shadow-foreground/10">
                          {loading ? '登录中...' : '登录后台'}
                          {!loading ? <ArrowRightIcon data-icon="inline-end" /> : null}
                        </Button>
                      </Field>
                    </FieldGroup>
                  </form>

                  <div className="mt-6 flex items-center justify-between gap-3 rounded-2xl border border-white/50 bg-background/62 px-4 py-3 text-xs text-muted-foreground dark:border-white/10 dark:bg-background/36">
                    <span>当前页面已支持深色主题与系统跟随。</span>
                    <span className="font-medium text-foreground">Theme-aware</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

export default Login
