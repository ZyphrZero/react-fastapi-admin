import { ChevronsUpDownIcon, Edit3Icon, InfoIcon, RefreshCcwIcon, SearchIcon, Trash2Icon, WaypointsIcon, XIcon } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import api from '@/api'
import ConfirmDialog from '@/components/ConfirmDialog'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useErrorHandler } from '@/hooks/useErrorHandler'

const getMethodVariant = (method) => {
  if (method === 'GET') return 'secondary'
  if (method === 'POST') return 'default'
  if (method === 'DELETE') return 'destructive'
  return 'outline'
}

const validateApiForm = (values) => {
  const errors = {}

  if (!values.summary.trim()) {
    errors.summary = '请输入 API 描述'
  } else if (values.summary.trim().length > 500) {
    errors.summary = 'API 描述不能超过 500 个字符'
  }

  if (!values.tags.trim()) {
    errors.tags = '请输入 API 标签'
  } else if (values.tags.trim().length > 100) {
    errors.tags = 'API 标签不能超过 100 个字符'
  }

  return errors
}

const normalizeTagOption = (tag) => {
  if (typeof tag === 'string') {
    return {
      key: tag,
      label: tag,
      value: tag,
      count: null,
    }
  }

  if (tag && typeof tag === 'object') {
    const fallbackValue = String(tag.value ?? tag.label ?? '')
    const displayLabel = tag.label ?? (fallbackValue || '未分类')

    return {
      key: fallbackValue || JSON.stringify(tag),
      label: String(displayLabel),
      value: fallbackValue,
      count: typeof tag.count === 'number' ? tag.count : null,
    }
  }

  return null
}

const ApiManagement = () => {
  const [loading, setLoading] = useState(false)
  const [apis, setApis] = useState([])
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [searchValues, setSearchValues] = useState({ path: '', summary: '', tags: [] })
  const [searchParams, setSearchParams] = useState({})
  const [availableTags, setAvailableTags] = useState([])
  const [refreshLoading, setRefreshLoading] = useState(false)

  const [modalVisible, setModalVisible] = useState(false)
  const [modalValues, setModalValues] = useState({ path: '', method: 'GET', summary: '', tags: '' })
  const [modalErrors, setModalErrors] = useState({})
  const [modalLoading, setModalLoading] = useState(false)
  const [editingApi, setEditingApi] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const { handleError, handleBusinessError, showSuccess } = useErrorHandler()

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const selectedTags = availableTags.filter((tag) => searchValues.tags.includes(tag.value))

  const fetchApis = useCallback(
    async (page = 1, size = 10, search = {}) => {
      setLoading(true)
      try {
        const response = await api.apis.getList({
          page,
          page_size: size,
          ...search,
        })
        setApis(response.data || [])
        setTotal(response.total || 0)
        setCurrentPage(response.page || page)
        setPageSize(response.page_size || size)
      } catch (error) {
        handleError(error, '获取 API 列表失败')
      } finally {
        setLoading(false)
      }
    },
    [handleError],
  )

  const fetchAllTags = useCallback(async () => {
    try {
      const response = await api.apis.getTags()
      const normalizedTags = Array.isArray(response.data)
        ? response.data.map(normalizeTagOption).filter(Boolean)
        : []

      setAvailableTags(normalizedTags)
    } catch (error) {
      handleError(error, '获取 API 标签失败')
    }
  }, [handleError])

  useEffect(() => {
    void fetchApis(1, 10, {})
    void fetchAllTags()
  }, [fetchAllTags, fetchApis])

  const refreshApis = async () => {
    await fetchApis(currentPage, pageSize, searchParams)
  }

  const handleSearch = async (event) => {
    event.preventDefault()

    const nextParams = {}
    if (searchValues.path.trim()) nextParams.path = searchValues.path.trim()
    if (searchValues.summary.trim()) nextParams.summary = searchValues.summary.trim()
    if (searchValues.tags.length > 0) nextParams.tags = searchValues.tags.join(',')

    setSearchParams(nextParams)
    await fetchApis(1, pageSize, nextParams)
  }

  const handleClearSearch = async () => {
    setSearchValues({ path: '', summary: '', tags: [] })
    setSearchParams({})
    await fetchApis(1, pageSize, {})
  }

  const handlePageChange = async (page) => {
    await fetchApis(page, pageSize, searchParams)
  }

  const openModal = (apiItem) => {
    if (!apiItem) return

    setEditingApi(apiItem)
    setModalVisible(true)
    setModalErrors({})
    setModalValues({
      path: apiItem.path || '',
      method: apiItem.method || 'GET',
      summary: apiItem.summary || '',
      tags: apiItem.tags || '',
    })
  }

  const closeModal = (open) => {
    setModalVisible(open)
    if (!open) {
      setEditingApi(null)
      setModalErrors({})
      setModalValues({ path: '', method: 'GET', summary: '', tags: '' })
    }
  }

  const handleSaveApi = async (event) => {
    event.preventDefault()

    if (!editingApi) return

    const nextErrors = validateApiForm(modalValues)
    if (Object.keys(nextErrors).length > 0) {
      setModalErrors(nextErrors)
      return
    }

    setModalLoading(true)
    try {
      await api.apis.update({
        id: editingApi.id,
        path: editingApi.path,
        method: editingApi.method,
        summary: modalValues.summary.trim(),
        tags: modalValues.tags.trim(),
      })
      showSuccess('API 信息更新成功')
      closeModal(false)
      await fetchApis(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, 'API 更新失败')
    } finally {
      setModalLoading(false)
    }
  }

  const handleDeleteApi = async () => {
    if (!deleteTarget) return

    try {
      await api.apis.delete({ api_id: deleteTarget.id })
      showSuccess('API 删除成功')
      setDeleteTarget(null)
      await fetchApis(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, 'API 删除失败')
    }
  }

  const handleRefreshApis = async () => {
    setRefreshLoading(true)
    try {
      await api.apis.refresh()
      showSuccess('API 列表刷新成功')
      await fetchApis(currentPage, pageSize, searchParams)
      await fetchAllTags()
    } catch (error) {
      handleBusinessError(error, 'API 刷新失败')
    } finally {
      setRefreshLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-3 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">API 管理</h1>
            <InfoIcon className="size-4 text-muted-foreground" />
          </div>
          <p className="text-sm text-muted-foreground">自动管理系统 API 接口，扫描代码同步接口信息</p>
        </div>
        <Button onClick={() => void handleRefreshApis()} disabled={refreshLoading}>
          <RefreshCcwIcon data-icon="inline-start" className={refreshLoading ? 'animate-spin' : undefined} />
          {refreshLoading ? '扫描中...' : '扫描系统 API'}
        </Button>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
          <CardDescription>按路径、描述和标签筛选接口</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <form className="grid gap-3 md:grid-cols-2 xl:grid-cols-[18rem_18rem_18rem_auto] xl:items-end" onSubmit={handleSearch}>
            <Input
              placeholder="API 路径"
              value={searchValues.path}
              onChange={(event) => setSearchValues((current) => ({ ...current, path: event.target.value }))}
            />
            <Input
              placeholder="API 描述"
              value={searchValues.summary}
              onChange={(event) => setSearchValues((current) => ({ ...current, summary: event.target.value }))}
            />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button type="button" variant="outline" className="w-full justify-between font-normal">
                  <span className="truncate text-left">
                    {selectedTags.length > 0
                      ? selectedTags.map((tag) => tag.label).join('、')
                      : '选择标签'}
                  </span>
                  <ChevronsUpDownIcon data-icon="inline-end" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-[var(--radix-dropdown-menu-trigger-width)]">
                <DropdownMenuLabel>标签筛选</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  {availableTags.map((tag) => (
                    <DropdownMenuCheckboxItem
                      key={tag.key}
                      checked={searchValues.tags.includes(tag.value)}
                      onSelect={(event) => event.preventDefault()}
                      onCheckedChange={(checked) =>
                        setSearchValues((current) => ({
                          ...current,
                          tags: checked
                            ? [...current.tags, tag.value]
                            : current.tags.filter((value) => value !== tag.value),
                        }))
                      }
                    >
                      <span className="flex-1">{tag.label}</span>
                      {tag.count ? <span className="text-xs text-muted-foreground">{tag.count}</span> : null}
                    </DropdownMenuCheckboxItem>
                  ))}
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
            <div className="flex flex-wrap gap-2">
              <Button type="submit" variant="outline" disabled={loading}>
                <SearchIcon data-icon="inline-start" />
                搜索
              </Button>
              <Button type="button" variant="outline" onClick={handleClearSearch}>
                <XIcon data-icon="inline-start" />
                清空
              </Button>
              <Button type="button" variant="outline" onClick={() => void refreshApis()} disabled={loading}>
                <RefreshCcwIcon data-icon="inline-start" />
                刷新
              </Button>
            </div>
          </form>

          {availableTags.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {(selectedTags.length > 0 ? selectedTags : availableTags).map((tag) => (
                <Badge key={tag.key} variant={selectedTags.length > 0 ? 'secondary' : 'outline'}>
                  {tag.label}
                  {tag.count ? ` (${tag.count})` : ''}
                </Badge>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API 列表</CardTitle>
          <CardDescription>共 {total} 条记录</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {apis.length > 0 ? (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>API 路径</TableHead>
                    <TableHead>请求方式</TableHead>
                    <TableHead>API 描述</TableHead>
                    <TableHead>API 标签</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {apis.map((apiItem) => (
                    <TableRow key={apiItem.id}>
                      <TableCell className="whitespace-normal">
                        <code className="rounded bg-muted px-2 py-1 text-xs">{apiItem.path || '-'}</code>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getMethodVariant(apiItem.method)}>{apiItem.method}</Badge>
                      </TableCell>
                      <TableCell className="whitespace-normal">{apiItem.summary || '-'}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{apiItem.tags || '未分类'}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">已同步</Badge>
                      </TableCell>
                      <TableCell>{apiItem.created_at ? new Date(apiItem.created_at).toLocaleString('zh-CN') : '-'}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" size="icon-sm" onClick={() => openModal(apiItem)}>
                            <Edit3Icon />
                            <span className="sr-only">编辑</span>
                          </Button>
                          <Button variant="destructive" size="icon-sm" onClick={() => setDeleteTarget(apiItem)}>
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
                <div className="flex gap-2">
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
                  <WaypointsIcon />
                </EmptyMedia>
                <EmptyTitle>暂无 API 数据</EmptyTitle>
                <EmptyDescription>请尝试刷新系统 API，或调整筛选条件后重试。</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </CardContent>
      </Card>

      <Dialog open={modalVisible} onOpenChange={closeModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑 API 信息</DialogTitle>
            <DialogDescription>路径和方法由系统自动扫描生成，只允许修改描述和标签。</DialogDescription>
          </DialogHeader>
          <form className="flex flex-col gap-4" onSubmit={handleSaveApi}>
            <div className="flex flex-col gap-2">
              <Label htmlFor="api-path">API 路径</Label>
              <Input id="api-path" value={modalValues.path} disabled />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="api-method">请求方法</Label>
              <Input id="api-method" value={modalValues.method} disabled />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="api-summary" required invalid={Boolean(modalErrors.summary)}>API 描述</Label>
              <Input
                id="api-summary"
                required
                value={modalValues.summary}
                onChange={(event) => {
                  setModalValues((current) => ({ ...current, summary: event.target.value }))
                  setModalErrors((current) => ({ ...current, summary: undefined }))
                }}
                aria-invalid={Boolean(modalErrors.summary)}
              />
              {modalErrors.summary ? <p className="text-xs text-destructive">{modalErrors.summary}</p> : null}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="api-tags" required invalid={Boolean(modalErrors.tags)}>API 标签</Label>
              <Input
                id="api-tags"
                required
                value={modalValues.tags}
                onChange={(event) => {
                  setModalValues((current) => ({ ...current, tags: event.target.value }))
                  setModalErrors((current) => ({ ...current, tags: undefined }))
                }}
                aria-invalid={Boolean(modalErrors.tags)}
              />
              {modalErrors.tags ? <p className="text-xs text-destructive">{modalErrors.tags}</p> : null}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => closeModal(false)}>
                取消
              </Button>
              <Button type="submit" disabled={modalLoading}>
                {modalLoading ? '更新中...' : '更新'}
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
        title="确认删除 API？"
        description={deleteTarget ? `删除接口 ${deleteTarget.method} ${deleteTarget.path} 后无法恢复。` : ''}
        confirmText="确认删除"
        destructive
        onConfirm={() => void handleDeleteApi()}
      />
    </div>
  )
}

export default ApiManagement
