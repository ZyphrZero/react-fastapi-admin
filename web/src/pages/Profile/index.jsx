import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  BadgeCheckIcon,
  KeyRoundIcon,
  MailIcon,
  PhoneIcon,
  SaveIcon,
  ShieldIcon,
  UserIcon,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import api from '@/api'
import PasswordStrengthIndicator from '@/components/PasswordStrengthIndicator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useErrorHandler } from '@/hooks/useErrorHandler'
import { clearSession, setStoredUserInfo } from '@/utils/session'

const phonePattern = /^1[3-9]\d{9}$/
const specialCharPattern = /[!@#$%^&*(),.?":{}|<>]/

const formatDate = (dateString) => {
  if (!dateString) return '暂无数据'
  return new Date(dateString).toLocaleString('zh-CN')
}

const getUserInitials = (userInfo) => {
  const source = userInfo?.nickname || userInfo?.username || '用户'
  return source.replace(/\s+/g, '').slice(0, 2).toUpperCase()
}

const validateProfileForm = (values) => {
  const errors = {}

  if (values.nickname && values.nickname.trim().length > 30) {
    errors.nickname = '昵称不能超过 30 个字符'
  }

  if (values.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
    errors.email = '请输入有效的邮箱地址'
  }

  if (values.phone && !phonePattern.test(values.phone.trim())) {
    errors.phone = '请输入正确的 11 位手机号码'
  }

  return errors
}

const validatePasswordForm = (values) => {
  const errors = {}

  if (!values.oldPassword) {
    errors.oldPassword = '请输入当前密码'
  }

  if (!values.newPassword) {
    errors.newPassword = '请输入新密码'
  } else {
    if (values.newPassword.length < 8) {
      errors.newPassword = '密码长度不能少于 8 个字符'
    } else if (!/[A-Z]/.test(values.newPassword)) {
      errors.newPassword = '密码必须包含至少一个大写字母'
    } else if (!/[a-z]/.test(values.newPassword)) {
      errors.newPassword = '密码必须包含至少一个小写字母'
    } else if (!/\d/.test(values.newPassword)) {
      errors.newPassword = '密码必须包含至少一个数字'
    } else if (!specialCharPattern.test(values.newPassword)) {
      errors.newPassword = '密码必须包含至少一个特殊字符'
    }
  }

  if (!values.confirmPassword) {
    errors.confirmPassword = '请确认新密码'
  } else if (values.confirmPassword !== values.newPassword) {
    errors.confirmPassword = '两次输入的密码不一致'
  }

  return errors
}

const Profile = () => {
  const [userInfo, setUserInfo] = useState({})
  const [loading, setLoading] = useState(false)
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordStrength, setPasswordStrength] = useState(null)
  const [profileValues, setProfileValues] = useState({
    nickname: '',
    email: '',
    phone: '',
  })
  const [passwordValues, setPasswordValues] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  })
  const [profileErrors, setProfileErrors] = useState({})
  const [passwordErrors, setPasswordErrors] = useState({})

  const navigate = useNavigate()
  const { handleError, handleBusinessError, showSuccess, showWarning, message } = useErrorHandler()

  const fetchUserInfo = useCallback(async () => {
    try {
      const response = await api.auth.getUserInfo()
      const nextUserInfo = response.data || {}

      setUserInfo(nextUserInfo)
      setProfileValues({
        nickname: nextUserInfo.nickname || '',
        email: nextUserInfo.email || '',
        phone: nextUserInfo.phone || '',
      })
    } catch (error) {
      handleError(error, '获取用户信息失败')
    }
  }, [handleError])

  useEffect(() => {
    void fetchUserInfo()
  }, [fetchUserInfo])

  const profileSummary = useMemo(
    () => [
      {
        key: 'name',
        label: '显示名称',
        value: userInfo.nickname || userInfo.username || '未设置',
        hint: `用户名 @${userInfo.username || '未设置'}`,
        icon: UserIcon,
      },
      {
        key: 'email',
        label: '邮箱地址',
        value: userInfo.email || '未设置',
        hint: '用于接收系统通知',
        icon: MailIcon,
      },
      {
        key: 'phone',
        label: '手机号码',
        value: userInfo.phone || '未设置',
        hint: '用于账户联系',
        icon: PhoneIcon,
      },
      {
        key: 'status',
        label: '账户状态',
        value: userInfo.is_active ? '正常' : '禁用',
        hint: userInfo.is_superuser ? '超级管理员' : '普通用户',
        icon: ShieldIcon,
      },
    ],
    [userInfo],
  )

  const updateProfileValue = (field, value) => {
    setProfileValues((current) => ({ ...current, [field]: value }))
    setProfileErrors((current) => ({ ...current, [field]: undefined }))
  }

  const updatePasswordValue = (field, value) => {
    setPasswordValues((current) => ({ ...current, [field]: value }))
    setPasswordErrors((current) => ({ ...current, [field]: undefined }))
  }

  const handleUpdateProfile = async (event) => {
    event.preventDefault()

    const nextErrors = validateProfileForm(profileValues)
    if (Object.keys(nextErrors).length > 0) {
      setProfileErrors(nextErrors)
      return
    }

    setLoading(true)
    try {
      const processedValues = {
        nickname: profileValues.nickname.trim() || undefined,
        email: profileValues.email.trim() || undefined,
        phone: profileValues.phone.trim() || undefined,
      }

      await api.auth.updateProfile(processedValues)
      showSuccess('个人信息更新成功')

      const response = await api.auth.getUserInfo()
      const nextUserInfo = response.data || {}

      setUserInfo(nextUserInfo)
      setStoredUserInfo(nextUserInfo)
      setProfileValues({
        nickname: nextUserInfo.nickname || '',
        email: nextUserInfo.email || '',
        phone: nextUserInfo.phone || '',
      })
    } catch (error) {
      handleBusinessError(error, '更新失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdatePassword = async (event) => {
    event.preventDefault()

    const nextErrors = validatePasswordForm(passwordValues)
    if (Object.keys(nextErrors).length > 0) {
      setPasswordErrors(nextErrors)
      return
    }

    if (passwordStrength && passwordStrength.score < 40) {
      showWarning('密码强度太弱，请设置更强的密码')
      return
    }

    setPasswordLoading(true)
    try {
      await api.auth.updatePassword({
        old_password: passwordValues.oldPassword,
        new_password: passwordValues.newPassword,
      })

      showSuccess('密码修改成功，请重新登录')
      setPasswordValues({
        oldPassword: '',
        newPassword: '',
        confirmPassword: '',
      })
      setPasswordStrength(null)

      window.setTimeout(() => {
        clearSession()
        navigate('/login')
      }, 1500)
    } catch (error) {
      handleBusinessError(error, '密码修改失败，请重试', (standardError) => {
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

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-3 border-b pb-5 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <Avatar size="lg" className="size-14">
            <AvatarFallback>{getUserInitials(userInfo)}</AvatarFallback>
          </Avatar>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">个人中心</h1>
            <p className="text-sm text-muted-foreground">管理您的个人信息和账户安全设置</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge variant={userInfo.is_active ? 'secondary' : 'outline'}>
            {userInfo.is_active ? '账户正常' : '账户禁用'}
          </Badge>
          {userInfo.is_superuser ? <Badge>超级管理员</Badge> : null}
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {profileSummary.map((item) => {
          const Icon = item.icon

          return (
            <Card key={item.key}>
              <CardHeader className="pb-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-col gap-1">
                    <CardDescription>{item.label}</CardDescription>
                    <CardTitle className="text-base">{item.value}</CardTitle>
                  </div>
                  <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                    <Icon />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-sm text-muted-foreground">{item.hint}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <CardHeader>
            <CardTitle>账户详情</CardTitle>
            <CardDescription>当前登录账户的基础资料</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex items-center gap-4">
              <Avatar size="lg" className="size-16">
                <AvatarFallback>{getUserInitials(userInfo)}</AvatarFallback>
              </Avatar>
              <div className="flex flex-col gap-1">
                <div className="text-base font-medium">{userInfo.nickname || userInfo.username || '未设置'}</div>
                <div className="text-sm text-muted-foreground">@{userInfo.username || '未设置'}</div>
              </div>
            </div>

            <div className="grid gap-3">
              <div className="flex items-center justify-between gap-3 border-b pb-3">
                <span className="text-sm text-muted-foreground">邮箱地址</span>
                <span className="text-sm">{userInfo.email || '未设置'}</span>
              </div>
              <div className="flex items-center justify-between gap-3 border-b pb-3">
                <span className="text-sm text-muted-foreground">手机号码</span>
                <span className="text-sm">{userInfo.phone || '未设置'}</span>
              </div>
              <div className="flex items-center justify-between gap-3 border-b pb-3">
                <span className="text-sm text-muted-foreground">创建时间</span>
                <span className="text-sm">{formatDate(userInfo.created_at)}</span>
              </div>
              <div className="flex items-center justify-between gap-3 border-b pb-3">
                <span className="text-sm text-muted-foreground">更新时间</span>
                <span className="text-sm">{formatDate(userInfo.updated_at)}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-muted-foreground">最后登录</span>
                <span className="text-sm">{formatDate(userInfo.last_login)}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Tabs defaultValue="profile">
          <TabsList>
            <TabsTrigger value="profile">修改信息</TabsTrigger>
            <TabsTrigger value="password">修改密码</TabsTrigger>
          </TabsList>

          <TabsContent value="profile">
            <Card>
              <CardHeader>
                <CardTitle>修改信息</CardTitle>
                <CardDescription>更新昵称、邮箱和手机号</CardDescription>
              </CardHeader>
              <CardContent>
                <form className="flex flex-col gap-4" onSubmit={handleUpdateProfile}>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="profile-username">用户名</Label>
                      <Input id="profile-username" value={userInfo.username || ''} disabled />
                    </div>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="profile-nickname" invalid={Boolean(profileErrors.nickname)}>昵称</Label>
                      <Input
                        id="profile-nickname"
                        value={profileValues.nickname}
                        onChange={(event) => updateProfileValue('nickname', event.target.value)}
                        aria-invalid={Boolean(profileErrors.nickname)}
                      />
                      {profileErrors.nickname ? <p className="text-xs text-destructive">{profileErrors.nickname}</p> : null}
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="profile-email" invalid={Boolean(profileErrors.email)}>邮箱地址</Label>
                      <Input
                        id="profile-email"
                        type="email"
                        autoComplete="email"
                        value={profileValues.email}
                        onChange={(event) => updateProfileValue('email', event.target.value)}
                        aria-invalid={Boolean(profileErrors.email)}
                      />
                      {profileErrors.email ? <p className="text-xs text-destructive">{profileErrors.email}</p> : null}
                    </div>
                    <div className="flex flex-col gap-2">
                      <Label htmlFor="profile-phone" invalid={Boolean(profileErrors.phone)}>手机号码</Label>
                      <Input
                        id="profile-phone"
                        autoComplete="tel"
                        maxLength={11}
                        value={profileValues.phone}
                        onChange={(event) => updateProfileValue('phone', event.target.value.replace(/[^\d]/g, ''))}
                        aria-invalid={Boolean(profileErrors.phone)}
                      />
                      {profileErrors.phone ? <p className="text-xs text-destructive">{profileErrors.phone}</p> : null}
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={loading}>
                      <SaveIcon data-icon="inline-start" />
                      {loading ? '保存中...' : '保存更改'}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="password">
            <Card>
              <CardHeader>
                <CardTitle>修改密码</CardTitle>
                <CardDescription>密码更新后需要重新登录</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <form className="flex flex-col gap-4" onSubmit={handleUpdatePassword}>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="old-password" required invalid={Boolean(passwordErrors.oldPassword)}>当前密码</Label>
                    <Input
                      id="old-password"
                      type="password"
                      required
                      autoComplete="current-password"
                      value={passwordValues.oldPassword}
                      onChange={(event) => updatePasswordValue('oldPassword', event.target.value)}
                      aria-invalid={Boolean(passwordErrors.oldPassword)}
                    />
                    {passwordErrors.oldPassword ? <p className="text-xs text-destructive">{passwordErrors.oldPassword}</p> : null}
                  </div>

                  <div className="flex flex-col gap-2">
                    <Label htmlFor="new-password" required invalid={Boolean(passwordErrors.newPassword)}>新密码</Label>
                    <Input
                      id="new-password"
                      type="password"
                      required
                      autoComplete="new-password"
                      value={passwordValues.newPassword}
                      onChange={(event) => updatePasswordValue('newPassword', event.target.value)}
                      aria-invalid={Boolean(passwordErrors.newPassword)}
                    />
                    {passwordErrors.newPassword ? <p className="text-xs text-destructive">{passwordErrors.newPassword}</p> : null}
                  </div>

                  <PasswordStrengthIndicator
                    password={passwordValues.newPassword}
                    onStrengthChange={setPasswordStrength}
                    showSuggestions
                  />

                  <div className="flex flex-col gap-2">
                    <Label htmlFor="confirm-password" required invalid={Boolean(passwordErrors.confirmPassword)}>确认新密码</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      required
                      autoComplete="new-password"
                      value={passwordValues.confirmPassword}
                      onChange={(event) => updatePasswordValue('confirmPassword', event.target.value)}
                      aria-invalid={Boolean(passwordErrors.confirmPassword)}
                    />
                    {passwordErrors.confirmPassword ? <p className="text-xs text-destructive">{passwordErrors.confirmPassword}</p> : null}
                  </div>

                  <div className="rounded-lg border bg-muted/20 p-3 text-sm text-muted-foreground">
                    <div className="mb-2 flex items-center gap-2 font-medium text-foreground">
                      <BadgeCheckIcon className="size-4 text-primary" />
                      密码安全建议
                    </div>
                    <ul className="grid gap-1">
                      <li>密码长度至少 8 个字符</li>
                      <li>同时包含大写字母、小写字母、数字和特殊字符</li>
                      <li>不要使用容易猜测的弱密码</li>
                    </ul>
                  </div>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={passwordLoading}>
                      <KeyRoundIcon data-icon="inline-start" />
                      {passwordLoading ? '修改中...' : '修改密码'}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default Profile
