import { useCallback, useEffect, useState } from 'react'
import { Edit3Icon, MenuIcon, PlusIcon, SearchIcon, ShieldIcon, Trash2Icon, WaypointsIcon, XIcon } from 'lucide-react'

import api from '@/api'
import ConfirmDialog from '@/components/ConfirmDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { useErrorHandler } from '@/hooks/useErrorHandler'

const DEFAULT_PAGE_SIZE = 20
const PAGE_SIZE_OPTIONS = ['20', '50', '100']

const validateRoleForm = (values) => {
  const errors = {}

  if (!values.name.trim()) {
    errors.name = '请输入角色名称'
  } else if (values.name.trim().length < 2 || values.name.trim().length > 20) {
    errors.name = '角色名称长度为 2-20 个字符'
  }

  if (values.desc.trim().length > 500) {
    errors.desc = '角色描述不能超过 500 个字符'
  }

  return errors
}

const getMenuNodeMeta = (menu) => {
  const path = menu.path ?? ''
  const title = menu.name ?? (path || '未命名菜单')

  return {
    path,
    title,
    children: Array.isArray(menu.children) ? menu.children : [],
  }
}

const collectLeafMenuPaths = (menu) => {
  const { path, children } = getMenuNodeMeta(menu)

  if (!children.length) {
    return path ? [path] : []
  }

  return children.flatMap((child) => collectLeafMenuPaths(child))
}

const resolveMenuCheckedState = (menu, checkedMenuPaths) => {
  const { path, children } = getMenuNodeMeta(menu)

  if (!children.length) {
    return checkedMenuPaths.includes(path)
  }

  const leafPaths = collectLeafMenuPaths(menu)
  const checkedLeafCount = leafPaths.filter((leafPath) => checkedMenuPaths.includes(leafPath)).length

  if (checkedLeafCount === 0) {
    return false
  }

  if (checkedLeafCount === leafPaths.length) {
    return true
  }

  return 'indeterminate'
}

const renderMenuTree = (nodes, checkedMenuPaths, toggleMenuSelection, depth = 0) =>
  nodes.map((menu) => {
    const { path, title, children } = getMenuNodeMeta(menu)

    return (
      <div key={path} className="flex flex-col gap-2">
        <Label className="items-start">
          <Checkbox
            checked={resolveMenuCheckedState(menu, checkedMenuPaths)}
            onCheckedChange={(checked) => toggleMenuSelection(menu, Boolean(checked))}
          />
          <span className={depth > 0 ? 'text-sm' : ''}>{title}</span>
        </Label>
        {children.length ? (
          <div className="ml-6 flex flex-col gap-2 border-l border-border pl-4">
            {renderMenuTree(children, checkedMenuPaths, toggleMenuSelection, depth + 1)}
          </div>
        ) : null}
      </div>
    )
  })

const collectAllApiIds = (apiGroups) => {
  if (!Array.isArray(apiGroups)) {
    return []
  }

  return [...new Set(apiGroups.flatMap((group) => (group.items || []).map((item) => item.id)))]
}

const collectGroupApiIds = (items) => [...new Set((items || []).map((item) => item.id))]

const countCheckedApiIds = (apiIds, checkedApiIds) =>
  apiIds.filter((apiId) => checkedApiIds.includes(apiId)).length

const RoleManagement = () => {
  const [loading, setLoading] = useState(false)
  const [roles, setRoles] = useState([])
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [searchValue, setSearchValue] = useState('')
  const [searchParams, setSearchParams] = useState({})

  const [permissionOptionsLoading, setPermissionOptionsLoading] = useState(false)
  const [permissionOptions, setPermissionOptions] = useState({ menu_tree: [], api_groups: [] })

  const [modalVisible, setModalVisible] = useState(false)
  const [modalValues, setModalValues] = useState({ name: '', desc: '' })
  const [modalErrors, setModalErrors] = useState({})
  const [editingRole, setEditingRole] = useState(null)
  const [modalLoading, setModalLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [checkedMenuPaths, setCheckedMenuPaths] = useState([])
  const [checkedApiIds, setCheckedApiIds] = useState([])
  const [deleteTarget, setDeleteTarget] = useState(null)

  const { handleError, handleBusinessError, showSuccess } = useErrorHandler()

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const allApiIds = collectAllApiIds(permissionOptions.api_groups)

  const fetchRoles = useCallback(
    async (page = 1, size = DEFAULT_PAGE_SIZE, search = {}) => {
      setLoading(true)
      try {
        const response = await api.roles.getList({
          page,
          page_size: size,
          ...search,
        })
        setRoles(response.data || [])
        setTotal(response.total || 0)
        setCurrentPage(response.page || page)
        setPageSize(response.page_size || size)
      } catch (error) {
        handleError(error, '获取角色列表失败')
      } finally {
        setLoading(false)
      }
    },
    [handleError],
  )

  const fetchPermissionOptions = useCallback(async () => {
    setPermissionOptionsLoading(true)
    try {
      const response = await api.roles.getPermissionOptions()
      setPermissionOptions(response.data || { menu_tree: [], api_groups: [] })
    } catch (error) {
      handleError(error, '获取权限资源失败')
    } finally {
      setPermissionOptionsLoading(false)
    }
  }, [handleError])

  useEffect(() => {
    void fetchRoles(1, DEFAULT_PAGE_SIZE, {})
    void fetchPermissionOptions()
  }, [fetchPermissionOptions, fetchRoles])

  const handleSearch = async (event) => {
    event.preventDefault()

    const nextParams = {}
    if (searchValue.trim()) {
      nextParams.role_name = searchValue.trim()
    }
    setSearchParams(nextParams)
    await fetchRoles(1, pageSize, nextParams)
  }

  const handleClearSearch = async () => {
    setSearchValue('')
    setSearchParams({})
    await fetchRoles(1, pageSize, {})
  }

  const handlePageChange = async (page, size = pageSize) => {
    await fetchRoles(page, size, searchParams)
  }

  const closeModal = (open) => {
    setModalVisible(open)
    if (!open) {
      setEditingRole(null)
      setModalValues({ name: '', desc: '' })
      setModalErrors({})
      setCheckedMenuPaths([])
      setCheckedApiIds([])
      setDetailLoading(false)
    }
  }

  const openModal = async (role = null) => {
    setEditingRole(role)
    setModalVisible(true)
    setModalErrors({})
    setCheckedMenuPaths([])
    setCheckedApiIds([])

    if (!role) {
      setModalValues({ name: '', desc: '' })
      return
    }

    setDetailLoading(true)
    try {
      const response = await api.roles.getById(role.id)
      const detail = response.data || {}

      setModalValues({
        name: detail.name || '',
        desc: detail.desc || '',
      })
      setCheckedMenuPaths(detail.menu_paths || [])
      setCheckedApiIds(detail.api_ids || [])
    } catch (error) {
      handleBusinessError(error, '获取角色详情失败')
      closeModal(false)
    } finally {
      setDetailLoading(false)
    }
  }

  const toggleMenuSelection = (menu, checked) => {
    const leafPaths = collectLeafMenuPaths(menu)

    setCheckedMenuPaths((current) => {
      if (checked) {
        return [...new Set([...current, ...leafPaths])]
      }

      return current.filter((item) => !leafPaths.includes(item))
    })
  }

  const toggleApiId = (apiId, checked) => {
    setCheckedApiIds((current) =>
      checked ? [...new Set([...current, apiId])] : current.filter((item) => item !== apiId),
    )
  }

  const handleSelectAllApis = () => {
    setCheckedApiIds(allApiIds)
  }

  const handleClearAllApis = () => {
    setCheckedApiIds([])
  }

  const handleSelectApiGroup = (apiIds) => {
    setCheckedApiIds((current) => [...new Set([...current, ...apiIds])])
  }

  const handleClearApiGroup = (apiIds) => {
    setCheckedApiIds((current) => current.filter((item) => !apiIds.includes(item)))
  }

  const handleSaveRole = async (event) => {
    event.preventDefault()

    const nextErrors = validateRoleForm(modalValues)
    if (Object.keys(nextErrors).length > 0) {
      setModalErrors(nextErrors)
      return
    }

    setModalLoading(true)
    try {
      const payload = {
        name: modalValues.name.trim(),
        desc: modalValues.desc.trim(),
        menu_paths: checkedMenuPaths,
        api_ids: checkedApiIds,
      }

      if (editingRole) {
        await api.roles.update({ ...payload, id: editingRole.id })
        showSuccess('角色更新成功')
      } else {
        await api.roles.create(payload)
        showSuccess('角色创建成功')
      }

      closeModal(false)
      await fetchRoles(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, editingRole ? '角色更新失败' : '角色创建失败')
    } finally {
      setModalLoading(false)
    }
  }

  const handleDeleteRole = async () => {
    if (!deleteTarget) {
      return
    }

    try {
      await api.roles.delete({ role_id: deleteTarget.id })
      showSuccess('角色删除成功')
      setDeleteTarget(null)
      await fetchRoles(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, '角色删除失败')
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-3 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">角色管理</h1>
          <p className="text-sm text-muted-foreground">管理角色基础信息、菜单权限和 API 权限</p>
        </div>
        <Button onClick={() => void openModal()}>
          <PlusIcon data-icon="inline-start" />
          新增角色
        </Button>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
          <CardDescription>按角色名称筛选</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 md:flex-row md:items-end" onSubmit={handleSearch}>
            <div className="w-full md:w-72">
              <Input value={searchValue} placeholder="角色名称" onChange={(event) => setSearchValue(event.target.value)} />
            </div>
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
          <CardTitle>角色列表</CardTitle>
          <CardDescription>共 {total} 条记录</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {roles.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>角色名称</TableHead>
                    <TableHead>角色描述</TableHead>
                    <TableHead>菜单权限</TableHead>
                    <TableHead>API 权限</TableHead>
                    <TableHead>用户数量</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {roles.map((role) => (
                    <TableRow key={role.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <ShieldIcon className="size-4 text-muted-foreground" />
                          {role.name || '-'}
                        </div>
                      </TableCell>
                      <TableCell className="whitespace-normal">{role.desc || '-'}</TableCell>
                      <TableCell><Badge variant="outline">{role.menu_count || 0} 项</Badge></TableCell>
                      <TableCell><Badge variant="outline">{role.api_count || 0} 项</Badge></TableCell>
                      <TableCell><Badge variant="secondary">{role.user_count || 0} 人</Badge></TableCell>
                      <TableCell>{role.created_at ? new Date(role.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="icon-sm" onClick={() => void openModal(role)}>
                            <Edit3Icon />
                            <span className="sr-only">编辑</span>
                          </Button>
                          <Button variant="destructive" size="icon-sm" onClick={() => setDeleteTarget(role)}>
                            <Trash2Icon />
                            <span className="sr-only">删除</span>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-muted-foreground">
                  第 {currentPage} / {totalPages} 页，共 {total} 条
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-muted-foreground">每页</span>
                  <Select value={String(pageSize)} onValueChange={(value) => void handlePageChange(1, Number(value))}>
                    <SelectTrigger className="w-28">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        {PAGE_SIZE_OPTIONS.map((size) => (
                          <SelectItem key={size} value={size}>
                            {size} 条
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
          ) : (
            <Empty className="border bg-muted/20 py-10">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <ShieldIcon />
                </EmptyMedia>
                <EmptyTitle>暂无角色数据</EmptyTitle>
                <EmptyDescription>调整筛选条件后重试，或先创建一个新角色。</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </CardContent>
      </Card>

      <Dialog open={modalVisible} onOpenChange={closeModal}>
        <DialogContent className="sm:max-w-5xl">
          <DialogHeader>
            <DialogTitle>{editingRole ? '编辑角色权限' : '新增角色'}</DialogTitle>
            <DialogDescription>维护角色信息并分配菜单与 API 权限</DialogDescription>
          </DialogHeader>

          {detailLoading ? (
            <div className="py-12 text-sm text-muted-foreground">加载角色详情中...</div>
          ) : (
            <form className="flex flex-col gap-4" onSubmit={handleSaveRole}>
              <FieldGroup className="grid gap-4 md:grid-cols-2">
                <Field data-invalid={Boolean(modalErrors.name)}>
                  <FieldLabel htmlFor="role-name" required>角色名称</FieldLabel>
                  <Input
                    id="role-name"
                    required
                    value={modalValues.name}
                    className="min-h-12"
                    onChange={(event) => {
                      setModalValues((current) => ({ ...current, name: event.target.value }))
                      setModalErrors((current) => ({ ...current, name: undefined }))
                    }}
                    aria-invalid={Boolean(modalErrors.name)}
                  />
                  <FieldError>{modalErrors.name}</FieldError>
                </Field>
                <Field data-invalid={Boolean(modalErrors.desc)}>
                  <FieldLabel htmlFor="role-desc">角色描述</FieldLabel>
                  <Textarea
                    id="role-desc"
                    value={modalValues.desc}
                    className="min-h-12"
                    onChange={(event) => {
                      setModalValues((current) => ({ ...current, desc: event.target.value }))
                      setModalErrors((current) => ({ ...current, desc: undefined }))
                    }}
                    aria-invalid={Boolean(modalErrors.desc)}
                  />
                  <FieldError>{modalErrors.desc}</FieldError>
                </Field>
              </FieldGroup>

              <div className="grid gap-4 xl:grid-cols-2">
                <Card size="sm">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MenuIcon className="size-4" />
                      菜单权限
                    </CardTitle>
                    <CardDescription>按菜单路径分配访问权限</CardDescription>
                  </CardHeader>
                  <CardContent className="max-h-[28rem] overflow-y-auto">
                    {permissionOptionsLoading ? (
                      <div className="text-sm text-muted-foreground">加载权限资源中...</div>
                    ) : permissionOptions.menu_tree?.length ? (
                      <div className="flex flex-col gap-3">
                        {renderMenuTree(permissionOptions.menu_tree, checkedMenuPaths, toggleMenuSelection)}
                      </div>
                    ) : (
                      <Empty className="border bg-muted/20 py-8">
                        <EmptyHeader>
                          <EmptyMedia variant="icon">
                            <MenuIcon />
                          </EmptyMedia>
                          <EmptyTitle>暂无可授权菜单</EmptyTitle>
                        </EmptyHeader>
                      </Empty>
                    )}
                  </CardContent>
                </Card>

                <Card size="sm">
                  <CardHeader>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          <WaypointsIcon className="size-4" />
                          API 权限
                        </CardTitle>
                        <CardDescription>按接口分组分配访问权限</CardDescription>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          已选 {checkedApiIds.length} / {allApiIds.length}
                        </span>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={permissionOptionsLoading || allApiIds.length === 0 || checkedApiIds.length === allApiIds.length}
                          onClick={handleSelectAllApis}
                        >
                          全选
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={permissionOptionsLoading || checkedApiIds.length === 0}
                          onClick={handleClearAllApis}
                        >
                          清空
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="max-h-[28rem] overflow-y-auto">
                    {permissionOptionsLoading ? (
                      <div className="text-sm text-muted-foreground">加载权限资源中...</div>
                    ) : permissionOptions.api_groups?.length ? (
                      <div className="flex flex-col gap-4">
                        {permissionOptions.api_groups.map((group) => {
                          const groupApiIds = collectGroupApiIds(group.items)
                          const checkedCount = countCheckedApiIds(groupApiIds, checkedApiIds)

                          return (
                            <div key={group.tag} className="rounded-lg border p-3">
                              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                                <div className="text-sm font-medium">
                                  {group.tag} ({group.items?.length || 0})
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs text-muted-foreground">
                                    已选 {checkedCount} / {groupApiIds.length}
                                  </span>
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    disabled={groupApiIds.length === 0 || checkedCount === groupApiIds.length}
                                    onClick={() => handleSelectApiGroup(groupApiIds)}
                                  >
                                    全选
                                  </Button>
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    disabled={checkedCount === 0}
                                    onClick={() => handleClearApiGroup(groupApiIds)}
                                  >
                                    清空
                                  </Button>
                                </div>
                              </div>
                              <div className="flex flex-col gap-2">
                                {(group.items || []).map((item) => (
                                  <Label key={item.id} className="items-start">
                                    <Checkbox
                                      checked={checkedApiIds.includes(item.id)}
                                      onCheckedChange={(checked) => toggleApiId(item.id, Boolean(checked))}
                                    />
                                    <div className="flex flex-col gap-1">
                                      <span className="font-mono text-xs text-muted-foreground">{item.method} {item.path}</span>
                                      <span>{item.summary || '未命名接口'}</span>
                                    </div>
                                  </Label>
                                ))}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <Empty className="border bg-muted/20 py-8">
                        <EmptyHeader>
                          <EmptyMedia variant="icon">
                            <WaypointsIcon />
                          </EmptyMedia>
                          <EmptyTitle>暂无可授权 API</EmptyTitle>
                        </EmptyHeader>
                      </Empty>
                    )}
                  </CardContent>
                </Card>
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => closeModal(false)}>
                  取消
                </Button>
                <Button type="submit" disabled={modalLoading}>
                  {modalLoading ? '提交中...' : editingRole ? '更新' : '创建'}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        title="确认删除角色？"
        description={deleteTarget ? `删除角色 ${deleteTarget.name} 后无法恢复，请谨慎操作。` : ''}
        confirmText="确认删除"
        destructive
        onConfirm={() => void handleDeleteRole()}
      />
    </div>
  )
}

export default RoleManagement
