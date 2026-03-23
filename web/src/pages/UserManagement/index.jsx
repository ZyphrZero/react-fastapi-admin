import { useCallback, useEffect, useState } from 'react'
import { ChevronsUpDownIcon, Edit3Icon, KeyRoundIcon, PlusIcon, SearchIcon, Trash2Icon, UserIcon, XIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import api from '@/api'
import ConfirmDialog from '@/components/ConfirmDialog'
import PasswordStrengthIndicator from '@/components/PasswordStrengthIndicator'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useErrorHandler } from '@/hooks/useErrorHandler'
import { usePasswordPolicy } from '@/hooks/usePasswordPolicy'
import { validatePasswordAgainstPolicy } from '@/utils/passwordStrength'
import { clearSession, getStoredUserInfo } from '@/utils/session'

const createEmptyUserForm = () => ({
  id: '',
  username: '',
  email: '',
  nickname: '',
  phone: '',
  password: '',
  confirmPassword: '',
  role_ids: [],
  is_active: true,
  is_superuser: false,
})

const createEmptyResetPasswordForm = () => ({
  newPassword: '',
  confirmNewPassword: '',
})

const validateUserForm = (values, editingUser, passwordPolicy) => {
  const errors = {}

  if (!values.username.trim()) {
    errors.username = '请输入用户名'
  } else if (values.username.trim().length < 3 || values.username.trim().length > 20) {
    errors.username = '用户名长度为 3-20 个字符'
  } else if (!/^[a-zA-Z0-9_]+$/.test(values.username.trim())) {
    errors.username = '用户名只能包含字母、数字和下划线'
  }

  if (values.nickname && values.nickname.trim().length > 30) {
    errors.nickname = '昵称不能超过 30 个字符'
  }

  if (!values.email.trim()) {
    errors.email = '请输入邮箱地址'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
    errors.email = '请输入正确的邮箱格式'
  }

  if (values.phone && !/^1[3-9]\d{9}$/.test(values.phone.trim())) {
    errors.phone = '请输入正确的手机号格式'
  }

  if (!editingUser) {
    const passwordError = validatePasswordAgainstPolicy(values.password, passwordPolicy)
    if (passwordError) {
      errors.password = passwordError
    }

    if (!values.confirmPassword) {
      errors.confirmPassword = '请确认密码'
    } else if (values.confirmPassword !== values.password) {
      errors.confirmPassword = '两次输入的密码不一致'
    }
  }

  return errors
}

const validateResetPasswordForm = (values, passwordPolicy) => {
  const errors = {}
  const passwordError = validatePasswordAgainstPolicy(values.newPassword, passwordPolicy)

  if (passwordError) {
    errors.newPassword = passwordError
  }

  if (!values.confirmNewPassword) {
    errors.confirmNewPassword = '请再次输入新密码'
  } else if (values.confirmNewPassword !== values.newPassword) {
    errors.confirmNewPassword = '两次输入的密码不一致'
  }

  return errors
}

const UserManagement = () => {
  const currentUser = getStoredUserInfo()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(false)
  const [users, setUsers] = useState([])
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [searchValues, setSearchValues] = useState({ username: '', nickname: '' })
  const [searchParams, setSearchParams] = useState({})
  const [modalVisible, setModalVisible] = useState(false)
  const [modalLoading, setModalLoading] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [modalValues, setModalValues] = useState(createEmptyUserForm())
  const [modalErrors, setModalErrors] = useState({})
  const [passwordStrength, setPasswordStrength] = useState(null)
  const [resetPasswordVisible, setResetPasswordVisible] = useState(false)
  const [resetPasswordTarget, setResetPasswordTarget] = useState(null)
  const [resetPasswordLoading, setResetPasswordLoading] = useState(false)
  const [resetPasswordValues, setResetPasswordValues] = useState(createEmptyResetPasswordForm())
  const [resetPasswordErrors, setResetPasswordErrors] = useState({})
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [roles, setRoles] = useState([])

  const { handleError, handleBusinessError, showSuccess } = useErrorHandler()
  const passwordPolicy = usePasswordPolicy()

  const isEditingCurrentUser = currentUser?.id === editingUser?.id
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const selectedRoles = roles.filter((role) => modalValues.role_ids.includes(role.id))

  const fetchUsers = useCallback(
    async (page = 1, size = 10, search = {}) => {
      setLoading(true)
      try {
        const response = await api.users.getList({
          page,
          page_size: size,
          ...search,
        })

        setUsers(response.data || [])
        setTotal(response.total || 0)
        setCurrentPage(response.page || page)
        setPageSize(response.page_size || size)
      } catch (error) {
        handleError(error, '获取用户列表失败')
      } finally {
        setLoading(false)
      }
    },
    [handleError],
  )

  const fetchRoles = useCallback(async () => {
    try {
      const response = await api.roles.getList({ page: 1, page_size: 1000 })
      setRoles(response.data || [])
    } catch (error) {
      handleError(error, '获取角色列表失败')
    }
  }, [handleError])

  useEffect(() => {
    void fetchUsers(1, 10, {})
    void fetchRoles()
  }, [fetchRoles, fetchUsers])

  const openModal = (user = null) => {
    setEditingUser(user)
    setModalVisible(true)
    setModalErrors({})
    setPasswordStrength(null)

    if (user) {
      setModalValues({
        id: String(user.id),
        username: user.username || '',
        email: user.email || '',
        nickname: user.nickname || '',
        phone: user.phone || '',
        password: '',
        confirmPassword: '',
        role_ids: user.roles?.map((role) => role.id) || [],
        is_active: Boolean(user.is_active),
        is_superuser: Boolean(user.is_superuser),
      })
    } else {
      setModalValues(createEmptyUserForm())
    }
  }

  const closeModal = (open) => {
    setModalVisible(open)
    if (!open) {
      setEditingUser(null)
      setModalValues(createEmptyUserForm())
      setModalErrors({})
      setPasswordStrength(null)
    }
  }

  const openResetPassword = (user) => {
    setResetPasswordTarget(user)
    setResetPasswordVisible(true)
    setResetPasswordValues(createEmptyResetPasswordForm())
    setResetPasswordErrors({})
    setPasswordStrength(null)
  }

  const closeResetPassword = (open) => {
    setResetPasswordVisible(open)
    if (!open) {
      setResetPasswordTarget(null)
      setResetPasswordValues(createEmptyResetPasswordForm())
      setResetPasswordErrors({})
      setPasswordStrength(null)
    }
  }

  const updateModalField = (field, value) => {
    setModalValues((current) => ({ ...current, [field]: value }))
    setModalErrors((current) => ({ ...current, [field]: undefined }))
  }

  const updateResetPasswordField = (field, value) => {
    setResetPasswordValues((current) => ({ ...current, [field]: value }))
    setResetPasswordErrors((current) => ({ ...current, [field]: undefined }))
  }

  const handleSearch = async (event) => {
    event.preventDefault()

    const nextParams = {}
    if (searchValues.username.trim()) nextParams.username = searchValues.username.trim()
    if (searchValues.nickname.trim()) nextParams.nickname = searchValues.nickname.trim()

    setSearchParams(nextParams)
    setCurrentPage(1)
    await fetchUsers(1, pageSize, nextParams)
  }

  const handleClearSearch = async () => {
    setSearchValues({ username: '', nickname: '' })
    setSearchParams({})
    setCurrentPage(1)
    await fetchUsers(1, pageSize, {})
  }

  const handlePageChange = async (page, size = pageSize) => {
    await fetchUsers(page, size, searchParams)
  }

  const handleSaveUser = async (event) => {
    event.preventDefault()

    const nextErrors = validateUserForm(modalValues, editingUser, passwordPolicy)
    if (Object.keys(nextErrors).length > 0) {
      setModalErrors(nextErrors)
      return
    }

    setModalLoading(true)
    try {
      const payload = {
        ...modalValues,
        username: modalValues.username.trim(),
        email: modalValues.email.trim(),
        nickname: modalValues.nickname.trim() || undefined,
        phone: modalValues.phone.trim() || undefined,
      }

      if (!editingUser) {
        payload.password = modalValues.password
      } else {
        delete payload.password
        delete payload.confirmPassword
      }

      delete payload.confirmPassword
      delete payload.id

      if (editingUser) {
        await api.users.update({ ...payload, id: editingUser.id })
        showSuccess('用户更新成功')
      } else {
        await api.users.create(payload)
        showSuccess('用户创建成功')
      }

      closeModal(false)
      await fetchUsers(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, editingUser ? '用户更新失败' : '用户创建失败')
    } finally {
      setModalLoading(false)
    }
  }

  const handleDeleteUser = async () => {
    if (!deleteTarget) {
      return
    }

    try {
      await api.users.delete({ user_id: deleteTarget.id })
      showSuccess('用户删除成功')
      setDeleteTarget(null)
      await fetchUsers(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, '用户删除失败')
    }
  }

  const handleResetPassword = async (event) => {
    event.preventDefault()

    if (!resetPasswordTarget) {
      return
    }

    const nextErrors = validateResetPasswordForm(resetPasswordValues, passwordPolicy)
    if (Object.keys(nextErrors).length > 0) {
      setResetPasswordErrors(nextErrors)
      return
    }

    setResetPasswordLoading(true)
    try {
      await api.users.resetPassword({
        user_id: resetPasswordTarget.id,
        new_password: resetPasswordValues.newPassword,
      })

      const isCurrentUser = currentUser?.id === resetPasswordTarget.id
      showSuccess(isCurrentUser ? '密码更新成功，请使用新密码重新登录' : '用户密码更新成功')
      closeResetPassword(false)

      if (isCurrentUser) {
        window.setTimeout(() => {
          clearSession()
          navigate('/login')
        }, 1200)
      }
    } catch (error) {
      handleBusinessError(error, '密码更新失败')
    } finally {
      setResetPasswordLoading(false)
    }
  }

  const renderTableContent = () => {
    if (users.length === 0) {
      return (
        <Empty className="border bg-muted/20 py-10">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <UserIcon />
            </EmptyMedia>
            <EmptyTitle>暂无用户数据</EmptyTitle>
            <EmptyDescription>调整筛选条件后重试，或先创建一个新用户。</EmptyDescription>
          </EmptyHeader>
        </Empty>
      )
    }

    return (
      <>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>用户名</TableHead>
              <TableHead>昵称</TableHead>
              <TableHead>邮箱</TableHead>
              <TableHead>手机号</TableHead>
              <TableHead>角色</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>创建时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => {
              const canResetPassword = !user.is_superuser || currentUser?.id === user.id

              return (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <UserIcon className="size-4 text-muted-foreground" />
                      {user.username || '-'}
                    </div>
                  </TableCell>
                  <TableCell>{user.nickname || '-'}</TableCell>
                  <TableCell>{user.email || '-'}</TableCell>
                  <TableCell>{user.phone || '-'}</TableCell>
                  <TableCell className="whitespace-normal">
                    <div className="flex flex-wrap gap-1">
                      {user.roles?.length > 0 ? (
                        user.roles.map((role) => (
                          <Badge key={role.id} variant="secondary">
                            {role.name}
                          </Badge>
                        ))
                      ) : (
                        <Badge variant="outline">未分配角色</Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-normal">
                    <div className="flex flex-wrap gap-1">
                      <Badge variant={user.is_active ? 'secondary' : 'outline'}>
                        {user.is_active ? '正常' : '禁用'}
                      </Badge>
                      {user.is_superuser ? <Badge>超级管理员</Badge> : null}
                    </div>
                  </TableCell>
                  <TableCell>{user.created_at ? new Date(user.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      <Button variant="outline" size="icon-sm" onClick={() => openModal(user)}>
                        <Edit3Icon />
                        <span className="sr-only">编辑</span>
                      </Button>
                      <Button
                        variant="outline"
                        size="icon-sm"
                        disabled={!canResetPassword}
                        onClick={() => openResetPassword(user)}
                      >
                        <KeyRoundIcon />
                        <span className="sr-only">重置密码</span>
                      </Button>
                      <Button variant="destructive" size="icon-sm" onClick={() => setDeleteTarget(user)}>
                        <Trash2Icon />
                        <span className="sr-only">删除</span>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>

        <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-muted-foreground">
            第 {currentPage} / {totalPages} 页，共 {total} 条
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Select value={String(pageSize)} onValueChange={(value) => void handlePageChange(1, Number(value))}>
              <SelectTrigger className="w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {['10', '20', '50', '100'].map((size) => (
                    <SelectItem key={size} value={size}>
                      {size} 条/页
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <Button variant="outline" disabled={currentPage <= 1 || loading} onClick={() => void handlePageChange(currentPage - 1)}>
              上一页
            </Button>
            <Button variant="outline" disabled={currentPage >= totalPages || loading} onClick={() => void handlePageChange(currentPage + 1)}>
              下一页
            </Button>
          </div>
        </div>
      </>
    )
  }

  const renderDialogs = () => (
    <>
      <Dialog open={modalVisible} onOpenChange={closeModal}>
        <DialogContent className="sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>{editingUser ? '编辑用户' : '新增用户'}</DialogTitle>
            <DialogDescription>维护用户基本信息和角色权限</DialogDescription>
          </DialogHeader>
          <form className="flex flex-col gap-4" onSubmit={handleSaveUser}>
            <FieldGroup className="grid gap-4 md:grid-cols-2">
              <Field data-invalid={Boolean(modalErrors.username)}>
                <FieldLabel htmlFor="modal-username" required>用户名</FieldLabel>
                <Input
                  id="modal-username"
                  name="username"
                  autoComplete="username"
                  value={modalValues.username}
                  required
                  disabled={Boolean(editingUser)}
                  onChange={(event) => updateModalField('username', event.target.value)}
                  aria-invalid={Boolean(modalErrors.username)}
                />
                <FieldError>{modalErrors.username}</FieldError>
              </Field>
              <Field data-invalid={Boolean(modalErrors.nickname)}>
                <FieldLabel htmlFor="modal-nickname">昵称</FieldLabel>
                <Input
                  id="modal-nickname"
                  value={modalValues.nickname}
                  onChange={(event) => updateModalField('nickname', event.target.value)}
                  aria-invalid={Boolean(modalErrors.nickname)}
                />
                <FieldError>{modalErrors.nickname}</FieldError>
              </Field>
            </FieldGroup>

            <FieldGroup className="grid gap-4 md:grid-cols-2">
              <Field data-invalid={Boolean(modalErrors.email)}>
                <FieldLabel htmlFor="modal-email" required>邮箱</FieldLabel>
                <Input
                  id="modal-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={modalValues.email}
                  onChange={(event) => updateModalField('email', event.target.value)}
                  aria-invalid={Boolean(modalErrors.email)}
                />
                <FieldError>{modalErrors.email}</FieldError>
              </Field>
              <Field data-invalid={Boolean(modalErrors.phone)}>
                <FieldLabel htmlFor="modal-phone">手机号</FieldLabel>
                <Input
                  id="modal-phone"
                  name="tel"
                  autoComplete="tel"
                  value={modalValues.phone}
                  onChange={(event) => updateModalField('phone', event.target.value.replace(/[^\d]/g, ''))}
                  aria-invalid={Boolean(modalErrors.phone)}
                />
                <FieldError>{modalErrors.phone}</FieldError>
              </Field>
            </FieldGroup>

            {!editingUser ? (
              <>
                <FieldGroup className="grid gap-4 md:grid-cols-2">
                  <Field data-invalid={Boolean(modalErrors.password)}>
                    <FieldLabel htmlFor="modal-password" required>密码</FieldLabel>
                    <Input
                      id="modal-password"
                      name="new-password"
                      type="password"
                      required
                      autoComplete="new-password"
                      value={modalValues.password}
                      onChange={(event) => updateModalField('password', event.target.value)}
                      aria-invalid={Boolean(modalErrors.password)}
                    />
                    <FieldError>{modalErrors.password}</FieldError>
                  </Field>
                  <Field data-invalid={Boolean(modalErrors.confirmPassword)}>
                    <FieldLabel htmlFor="modal-confirm-password" required>确认密码</FieldLabel>
                    <Input
                      id="modal-confirm-password"
                      name="confirm-new-password"
                      type="password"
                      required
                      autoComplete="new-password"
                      value={modalValues.confirmPassword}
                      onChange={(event) => updateModalField('confirmPassword', event.target.value)}
                      aria-invalid={Boolean(modalErrors.confirmPassword)}
                    />
                    <FieldError>{modalErrors.confirmPassword}</FieldError>
                  </Field>
                </FieldGroup>

                <PasswordStrengthIndicator
                  password={modalValues.password}
                  policy={passwordPolicy}
                  onStrengthChange={setPasswordStrength}
                  showSuggestions
                />
              </>
            ) : null}

            <FieldGroup className="grid gap-4 md:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="user-active-status">账户状态</FieldLabel>
                <Select
                  value={modalValues.is_active ? 'true' : 'false'}
                  onValueChange={(value) => updateModalField('is_active', value === 'true')}
                >
                  <SelectTrigger id="user-active-status" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="true">正常</SelectItem>
                      <SelectItem value="false" disabled={isEditingCurrentUser}>
                        禁用
                      </SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel htmlFor="user-superuser-status">超级管理员</FieldLabel>
                <Select
                  value={modalValues.is_superuser ? 'true' : 'false'}
                  onValueChange={(value) => updateModalField('is_superuser', value === 'true')}
                >
                  <SelectTrigger id="user-superuser-status" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="false">否</SelectItem>
                      <SelectItem value="true">是</SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
            </FieldGroup>

            <Field>
              <FieldLabel>用户角色</FieldLabel>
              <div className="rounded-lg border p-3">
                {roles.length > 0 ? (
                  <div className="flex flex-col gap-3">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button type="button" variant="outline" className="w-full justify-between">
                          <span className="truncate">
                            {selectedRoles.length > 0
                              ? selectedRoles.map((role) => role.name).join('、')
                              : '请选择角色'}
                          </span>
                          <ChevronsUpDownIcon data-icon="inline-end" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start" className="w-[var(--radix-dropdown-menu-trigger-width)]">
                        <DropdownMenuLabel>选择用户角色</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuGroup>
                          {roles.map((role) => (
                            <DropdownMenuCheckboxItem
                              key={role.id}
                              checked={modalValues.role_ids.includes(role.id)}
                              onSelect={(event) => event.preventDefault()}
                              onCheckedChange={(checked) => {
                                setModalValues((current) => ({
                                  ...current,
                                  role_ids: checked
                                    ? [...current.role_ids, role.id]
                                    : current.role_ids.filter((currentRoleId) => currentRoleId !== role.id),
                                }))
                              }}
                            >
                              <div className="flex min-w-0 flex-col gap-0.5">
                                <span>{role.name}</span>
                                <span className="truncate text-xs text-muted-foreground">{role.desc || '暂无描述'}</span>
                              </div>
                            </DropdownMenuCheckboxItem>
                          ))}
                        </DropdownMenuGroup>
                      </DropdownMenuContent>
                    </DropdownMenu>

                    {selectedRoles.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {selectedRoles.map((role) => (
                          <Badge key={role.id} variant="secondary">
                            {role.name}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">未选择角色</p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">暂无可选角色</p>
                )}
              </div>
            </Field>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => closeModal(false)}>
                取消
              </Button>
              <Button type="submit" disabled={modalLoading || (!editingUser && passwordStrength?.score === 0)}>
                {modalLoading ? '提交中...' : editingUser ? '更新' : '创建'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={resetPasswordVisible} onOpenChange={closeResetPassword}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {resetPasswordTarget?.username ? `为 ${resetPasswordTarget.username} 设置新密码` : '设置新密码'}
            </DialogTitle>
            <DialogDescription>请设置符合安全策略的新密码</DialogDescription>
          </DialogHeader>

          <form className="flex flex-col gap-4" onSubmit={handleResetPassword}>
            <Input
              tabIndex={-1}
              aria-hidden="true"
              className="sr-only"
              name="username"
              autoComplete="username"
              value={resetPasswordTarget?.username || ''}
              readOnly
            />
            <FieldGroup>
              <Field data-invalid={Boolean(resetPasswordErrors.newPassword)}>
                <FieldLabel htmlFor="reset-password" required>新密码</FieldLabel>
              <Input
                id="reset-password"
                name="new-password"
                type="password"
                required
                autoComplete="new-password"
                value={resetPasswordValues.newPassword}
                onChange={(event) => updateResetPasswordField('newPassword', event.target.value)}
                aria-invalid={Boolean(resetPasswordErrors.newPassword)}
              />
                <FieldError>{resetPasswordErrors.newPassword}</FieldError>
              </Field>

              <PasswordStrengthIndicator
                password={resetPasswordValues.newPassword}
                policy={passwordPolicy}
                onStrengthChange={setPasswordStrength}
                showSuggestions
              />

              <Field data-invalid={Boolean(resetPasswordErrors.confirmNewPassword)}>
                <FieldLabel htmlFor="reset-confirm-password" required>确认新密码</FieldLabel>
                <Input
                  id="reset-confirm-password"
                  name="confirm-new-password"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={resetPasswordValues.confirmNewPassword}
                  onChange={(event) => updateResetPasswordField('confirmNewPassword', event.target.value)}
                  aria-invalid={Boolean(resetPasswordErrors.confirmNewPassword)}
                />
                <FieldError>{resetPasswordErrors.confirmNewPassword}</FieldError>
              </Field>
            </FieldGroup>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => closeResetPassword(false)}>
                取消
              </Button>
              <Button type="submit" disabled={resetPasswordLoading}>
                {resetPasswordLoading ? '更新中...' : '更新密码'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        title="确认删除用户？"
        description={deleteTarget ? `删除用户 ${deleteTarget.username} 后无法恢复，请谨慎操作。` : ''}
        confirmText="确认删除"
        destructive
        onConfirm={() => void handleDeleteUser()}
      />
    </>
  )

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-3 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">用户管理</h1>
          <p className="text-sm text-muted-foreground">管理用户账户、角色权限和基础信息</p>
        </div>
        <Button onClick={() => openModal()}>
          <PlusIcon data-icon="inline-start" />
          新增用户
        </Button>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
          <CardDescription>按用户名和昵称筛选用户</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSearch}>
            <FieldGroup className="grid gap-3 md:grid-cols-2 xl:grid-cols-[18rem_18rem_auto] xl:items-end">
              <Field>
                <FieldLabel htmlFor="user-search-username">用户名</FieldLabel>
                <Input
                  id="user-search-username"
                  placeholder="例如 admin"
                  value={searchValues.username}
                  onChange={(event) => setSearchValues((current) => ({ ...current, username: event.target.value }))}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="user-search-nickname">昵称</FieldLabel>
                <Input
                  id="user-search-nickname"
                  placeholder="例如 管理员"
                  value={searchValues.nickname}
                  onChange={(event) => setSearchValues((current) => ({ ...current, nickname: event.target.value }))}
                />
              </Field>
            </FieldGroup>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" variant="outline" disabled={loading}>
                <SearchIcon data-icon="inline-start" />
                搜索
              </Button>
              <Button type="button" variant="outline" onClick={handleClearSearch}>
                <XIcon data-icon="inline-start" />
                清空
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>用户列表</CardTitle>
          <CardDescription>共 {total} 条记录</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">{renderTableContent()}</CardContent>
      </Card>

      {renderDialogs()}
    </div>
  )
}

export default UserManagement
