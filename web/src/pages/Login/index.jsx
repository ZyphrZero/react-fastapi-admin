import { useEffect, useMemo, useState } from 'react'
import { ArrowRightIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import api from '@/api'
import BrandLogo from '@/components/BrandLogo'
import { LoginPageImageStage } from '@/components/LoginPageImageStage'
import { ModeToggle } from '@/components/mode-toggle'
import { useTheme } from '@/components/theme-provider'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useAppMeta } from '@/hooks/useAppMeta'
import { useErrorHandler } from '@/hooks/useErrorHandler'
import { findFirstAccessiblePath } from '@/utils/permission'
import {
  clearSession,
  markRefreshSession,
  setAccessToken,
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
  const appMeta = useAppMeta()
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

  useEffect(() => {
    document.title = `登录 - ${appMeta.app_title || 'React Go Admin'}`
  }, [appMeta.app_title])

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
      markRefreshSession(true)

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
      className="relative min-h-svh overflow-hidden"
      style={loginBackgroundStyle}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_16%,rgba(255,255,255,0.42),transparent_26%),radial-gradient(circle_at_78%_20%,rgba(255,255,255,0.3),transparent_24%),radial-gradient(circle_at_24%_82%,rgba(255,255,255,0.22),transparent_24%),radial-gradient(circle_at_84%_74%,rgba(255,255,255,0.18),transparent_22%)] dark:bg-[radial-gradient(circle_at_18%_16%,rgba(255,255,255,0.05),transparent_24%),radial-gradient(circle_at_78%_20%,rgba(255,255,255,0.04),transparent_22%),radial-gradient(circle_at_24%_82%,rgba(255,255,255,0.03),transparent_22%),radial-gradient(circle_at_84%_74%,rgba(255,255,255,0.03),transparent_20%)]" />
      <div className="pointer-events-none absolute left-[8%] top-[10%] size-44 rounded-full bg-rose-300/14 blur-3xl dark:bg-rose-500/8" />
      <div className="pointer-events-none absolute right-[12%] top-[18%] size-40 rounded-full bg-sky-200/12 blur-3xl dark:bg-cyan-400/7" />
      <div className="pointer-events-none absolute left-[18%] bottom-[14%] size-36 rounded-full bg-amber-200/10 blur-3xl dark:bg-amber-400/6" />
      <div className="pointer-events-none absolute right-[18%] bottom-[10%] size-48 rounded-full bg-fuchsia-200/10 blur-3xl dark:bg-indigo-500/7" />

      <div className="absolute right-4 top-4 z-20 sm:right-6 sm:top-6">
        <ModeToggle className="border-border/60 bg-background/80 shadow-sm backdrop-blur" />
      </div>

      <div className="relative z-10 flex min-h-svh items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
        <div className="relative w-full max-w-[58rem]">
          <div className="relative grid overflow-hidden rounded-[2rem] border border-border/60 bg-background shadow-[0_28px_80px_rgba(15,23,42,0.12),0_12px_28px_rgba(15,23,42,0.08)] dark:border-white/10 dark:shadow-[0_30px_90px_rgba(2,6,23,0.58),0_12px_32px_rgba(2,6,23,0.3)] lg:min-h-[39rem] lg:grid-cols-[minmax(0,28rem)_minmax(0,1fr)]">
            <section className="bg-background px-6 py-6 sm:px-10 sm:py-7">
              <div className="mx-auto flex h-full max-w-sm flex-col">
                <BrandLogo
                  className="items-start"
                  markClassName="size-10"
                  title={appMeta.app_title || 'React Go Admin'}
                  subtitle={appMeta.project_name && appMeta.project_name !== appMeta.app_title ? appMeta.project_name : 'CONTROL CENTER'}
                />

                <div className="flex flex-col gap-4 pt-5">
                  <div className="flex flex-col gap-2">
                    <Badge variant="outline" className="w-fit rounded-full px-3 py-1 text-[11px] uppercase tracking-[0.2em]">
                      Secure Access
                    </Badge>
                    <div className="space-y-1">
                      <h1 className="text-[2.1rem] font-semibold tracking-[-0.04em] text-foreground sm:text-[2.5rem]">
                        WelcomeBack
                      </h1>
                      <p className="max-w-sm text-sm leading-6 text-muted-foreground">
                        使用你的账户继续进入 {appMeta.app_title || 'React Go Admin'} 管理台。
                      </p>
                    </div>
                  </div>

                  <form onSubmit={handleSubmit} className="flex flex-col gap-7 pt-1">
                    <FieldGroup className="gap-4">
                      <Field data-invalid={Boolean(fieldErrors.username)}>
                        <FieldLabel htmlFor="username" required>用户名</FieldLabel>
                        <Input
                          id="username"
                          name="username"
                          autoComplete="username"
                          required
                          className="h-11 rounded-xl bg-background px-3"
                          placeholder="请输入用户名"
                          value={formValues.username}
                          onChange={(event) => updateField('username', event.target.value)}
                          aria-invalid={Boolean(fieldErrors.username)}
                        />
                        <FieldError>{fieldErrors.username}</FieldError>
                      </Field>

                      <Field data-invalid={Boolean(fieldErrors.password)}>
                        <FieldLabel htmlFor="password" required>密码</FieldLabel>
                        <Input
                          id="password"
                          name="password"
                          type="password"
                          required
                          autoComplete="current-password"
                          className="h-11 rounded-xl bg-background px-3"
                          placeholder="请输入密码"
                          value={formValues.password}
                          onChange={(event) => updateField('password', event.target.value)}
                          aria-invalid={Boolean(fieldErrors.password)}
                        />
                        <FieldError>{fieldErrors.password}</FieldError>
                      </Field>
                    </FieldGroup>

                    <Button
                      type="submit"
                      size="lg"
                      variant="outline"
                      disabled={loading || !formIsValid}
                      className="mx-auto h-12 w-[88%] rounded-[1.45rem] border-slate-300/85 bg-white/72 text-slate-900 shadow-[0_12px_28px_rgba(148,163,184,0.18)] backdrop-blur-md transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white/84 hover:shadow-[0_16px_34px_rgba(148,163,184,0.22)] focus-visible:ring-slate-300/55 disabled:opacity-100 disabled:border-slate-200/80 disabled:bg-white/58 disabled:text-slate-500 disabled:shadow-none disabled:hover:translate-y-0 dark:border-white/15 dark:bg-white/12 dark:text-white dark:shadow-[0_14px_30px_rgba(2,6,23,0.3)] dark:hover:border-white/22 dark:hover:bg-white/16 dark:hover:shadow-[0_18px_36px_rgba(2,6,23,0.36)] dark:disabled:border-white/10 dark:disabled:bg-white/8 dark:disabled:text-white/45"
                    >
                      <span className="pointer-events-none absolute inset-x-4 top-1 h-3 rounded-full bg-white/75 blur-sm dark:bg-white/14" />
                      <span className="pointer-events-none absolute inset-[1px] rounded-[1.35rem] border border-white/55 dark:border-white/10" />
                      <span className="relative z-10 flex items-center gap-2 font-semibold tracking-[-0.01em]">
                        {loading ? '登录中...' : '登录后台'}
                        {!loading ? <ArrowRightIcon data-icon="inline-end" /> : null}
                      </span>
                    </Button>
                  </form>
                </div>
              </div>
            </section>

            <section className="relative hidden border-l border-border/60 bg-stone-100 lg:flex dark:bg-muted/20">
              <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(255,255,255,0.5),transparent_38%)] dark:bg-[linear-gradient(180deg,rgba(255,255,255,0.03),transparent_38%)]" />
              <div className="relative flex flex-1 items-stretch justify-stretch">
                <LoginPageImageStage
                  src={appMeta.login_page_image_url}
                  mode={appMeta.login_page_image_mode || 'contain'}
                  zoom={appMeta.login_page_image_zoom ?? 1}
                  positionX={appMeta.login_page_image_position_x ?? 50}
                  positionY={appMeta.login_page_image_position_y ?? 50}
                  fillParent
                />
              </div>
            </section>
          </div>

          <p className="mt-5 text-center text-xs leading-6 text-muted-foreground">
            登录后会自动同步用户信息、菜单与 API 权限，并跳转到你当前可访问的页面。
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login
