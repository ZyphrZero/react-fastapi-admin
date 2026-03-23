import { memo, useCallback, useEffect, useMemo, useState } from 'react'
import {
  CopyIcon,
  DownloadIcon,
  EyeIcon,
  FileSearchIcon,
  InfoIcon,
  SearchIcon,
  Trash2Icon,
  XIcon,
} from 'lucide-react'

import api from '@/api'
import DateTimePicker from '@/components/DateTimePicker'
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
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useErrorHandler } from '@/hooks/useErrorHandler'
import { getStoredUserInfo } from '@/utils/session'

const DEFAULT_PAGE_SIZE = 100
const PAGE_SIZE_OPTIONS = ['20', '50', '100', '200']
const methodOptions = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
const logLevelOptions = ['info', 'warning', 'error']
const statusOptions = ['200', '201', '400', '401', '403', '404', '422', '500']

const formatDateTime = (value) => (value ? new Date(value).toLocaleString('zh-CN') : '-')

const formatJsonBlock = (value) => {
  if (value === null || typeof value === 'undefined' || value === '') {
    return '暂无数据'
  }

  if (typeof value === 'string') {
    return value
  }

  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

const normalizeDateTimeLocal = (value) => {
  if (!value) return ''
  return value.length === 16 ? `${value}:00` : value
}

const buildSearchParams = (values = {}) => {
  const nextParams = {}

  if (values.username?.trim()) nextParams.username = values.username.trim()
  if (values.module?.trim()) nextParams.module = values.module.trim()
  if (values.summary?.trim()) nextParams.summary = values.summary.trim()
  if (values.method && values.method !== 'all') nextParams.method = values.method
  if (values.status && values.status !== 'all') nextParams.status = Number(values.status)
  if (values.ip_address?.trim()) nextParams.ip_address = values.ip_address.trim()
  if (values.operation_type?.trim()) nextParams.operation_type = values.operation_type.trim()
  if (values.log_level && values.log_level !== 'all') nextParams.log_level = values.log_level
  if (values.start_time) nextParams.start_time = normalizeDateTimeLocal(values.start_time)
  if (values.end_time) nextParams.end_time = normalizeDateTimeLocal(values.end_time)

  return nextParams
}

const parseExportFileName = (message = '') => {
  const match = String(message).match(/([A-Za-z0-9._-]+\.csv)/)
  return match?.[1] || ''
}

const wait = (timeout = 1200) =>
  new Promise((resolve) => {
    window.setTimeout(resolve, timeout)
  })

const downloadBlobFile = (blob, filename) => {
  const downloadUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
}

const getMethodVariant = (method) => {
  if (method === 'GET') return 'secondary'
  if (method === 'POST') return 'default'
  if (method === 'DELETE') return 'destructive'
  return 'outline'
}

const getStatusVariant = (status) => {
  if (status >= 500) return 'destructive'
  if (status >= 400) return 'outline'
  return 'secondary'
}

const getLogLevelVariant = (level) => {
  if (level === 'error') return 'destructive'
  if (level === 'warning') return 'outline'
  return 'secondary'
}

const DetailItem = ({ label, children, className }) => (
  <div className={className}>
    <div className="mb-1 text-xs text-muted-foreground">{label}</div>
    <div className="text-sm leading-6 text-foreground">{children}</div>
  </div>
)

const DetailSection = ({ title, children, className }) => (
  <section className={className}>
    <div className="mb-3 text-sm font-medium text-foreground">{title}</div>
    <div className="grid gap-4">{children}</div>
  </section>
)

const DetailCodeBlock = ({ value }) => (
  <pre className="max-h-[48vh] overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-950 p-4 text-xs leading-6 text-slate-100">
    {formatJsonBlock(value)}
  </pre>
)

const AuditLogTableRow = memo(function AuditLogTableRow({
  isSelected,
  isSuperuser,
  log,
  onDelete,
  onOpenDetail,
  onToggleSelectedRow,
}) {
  return (
    <TableRow data-state={isSelected ? 'selected' : undefined} onDoubleClick={() => void onOpenDetail(log)}>
      {isSuperuser ? (
        <TableCell>
          <Checkbox checked={isSelected} onCheckedChange={(checked) => onToggleSelectedRow(log.id, Boolean(checked))} />
        </TableCell>
      ) : null}
      <TableCell className="whitespace-normal">
        <div className="flex flex-col gap-1">
          <div className="font-medium">{formatDateTime(log.created_at)}</div>
          <div className="text-xs text-muted-foreground">日志时间点</div>
        </div>
      </TableCell>
      <TableCell className="whitespace-normal">
        <div className="flex flex-col gap-1">
          <div className="font-medium">{log.username || 'system'}</div>
          <div className="text-xs text-muted-foreground">用户 ID: {log.user_id || '-'}</div>
        </div>
      </TableCell>
      <TableCell className="whitespace-normal">
        <div className="flex flex-col gap-2">
          <Badge variant="outline">{log.module || '基础模块'}</Badge>
          <div className="text-sm">{log.summary || '-'}</div>
        </div>
      </TableCell>
      <TableCell className="whitespace-normal">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Badge variant={getMethodVariant(log.method)}>{log.method || '-'}</Badge>
            <Badge variant={getLogLevelVariant(log.log_level)}>{log.log_level || 'unknown'}</Badge>
          </div>
          <code className="break-all rounded bg-muted px-2 py-1 text-xs">{log.path || '-'}</code>
        </div>
      </TableCell>
      <TableCell className="whitespace-normal">
        <div className="flex flex-col gap-2">
          <Badge variant={getStatusVariant(log.status)}>{log.status ?? '-'}</Badge>
          <div className="text-xs text-muted-foreground">{log.operation_type || '未分类操作'}</div>
        </div>
      </TableCell>
      <TableCell className="whitespace-normal">
        <div className="flex flex-col gap-1">
          <div className="font-medium">{log.response_time || 0} ms</div>
          <div className="text-xs text-muted-foreground">{log.ip_address || '-'}</div>
        </div>
      </TableCell>
      <TableCell>
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="icon-sm" onClick={() => void onOpenDetail(log)}>
            <EyeIcon />
            <span className="sr-only">查看详情</span>
          </Button>
          {isSuperuser ? (
            <Button variant="destructive" size="icon-sm" onClick={() => onDelete(log)}>
              <Trash2Icon />
              <span className="sr-only">删除日志</span>
            </Button>
          ) : null}
        </div>
      </TableCell>
    </TableRow>
  )
})

const AuditLog = () => {
  const currentUser = getStoredUserInfo()
  const isSuperuser = Boolean(currentUser?.is_superuser)

  const [loading, setLoading] = useState(false)
  const [exportLoading, setExportLoading] = useState(false)
  const [downloadLoading, setDownloadLoading] = useState(false)
  const [clearLoading, setClearLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)

  const [auditLogs, setAuditLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [hasMore, setHasMore] = useState(false)
  const [nextCursor, setNextCursor] = useState(null)
  const [cursorHistory, setCursorHistory] = useState([null])
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [latestExportFile, setLatestExportFile] = useState('')
  const [searchValues, setSearchValues] = useState({
    username: '',
    module: '',
    summary: '',
    method: 'all',
    status: 'all',
    ip_address: '',
    operation_type: '',
    log_level: 'all',
    start_time: '',
    end_time: '',
  })
  const [searchParams, setSearchParams] = useState({})

  const [detailOpen, setDetailOpen] = useState(false)
  const [activeLog, setActiveLog] = useState(null)
  const [clearModalVisible, setClearModalVisible] = useState(false)
  const [clearDays, setClearDays] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [batchDeleteVisible, setBatchDeleteVisible] = useState(false)

  const { handleError, handleBusinessError, handleSilentError, showInfo, showSuccess, showWarning } = useErrorHandler()
  const selectedRowKeySet = useMemo(() => new Set(selectedRowKeys), [selectedRowKeys])
  const allRowsSelected = auditLogs.length > 0 && selectedRowKeys.length === auditLogs.length

  const fetchAuditLogs = useCallback(
    async (cursor = null, size = DEFAULT_PAGE_SIZE, nextSearchParams = {}, page = 1) => {
      setLoading(true)
      try {
        const response = await api.auditLogs.getList({
          page_size: size,
          ...(cursor ? { cursor } : {}),
          ...nextSearchParams,
        })

        setAuditLogs(response.data || [])
        setTotal(response.total || 0)
        setHasMore(Boolean(response.has_more))
        setNextCursor(response.next_cursor || null)
        setCurrentPage(page)
        setPageSize(response.page_size || size)
        return response
      } catch (error) {
        handleError(error, '获取审计日志失败')
        return null
      } finally {
        setLoading(false)
      }
    },
    [handleError],
  )

  useEffect(() => {
    void fetchAuditLogs(null, DEFAULT_PAGE_SIZE, {}, 1)
  }, [fetchAuditLogs])

  const refreshCurrentPage = useCallback(async () => {
    const currentCursor = cursorHistory[currentPage - 1] || null
    const response = await fetchAuditLogs(currentCursor, pageSize, searchParams, currentPage)
    const currentData = response?.data || []

    if (currentData.length === 0 && currentPage > 1) {
      const previousPage = currentPage - 1
      const previousCursor = cursorHistory[previousPage - 1] || null
      setCursorHistory((previous) => previous.slice(0, previousPage))
      await fetchAuditLogs(previousCursor, pageSize, searchParams, previousPage)
    }
  }, [cursorHistory, currentPage, fetchAuditLogs, pageSize, searchParams])

  const handleSearch = async (event) => {
    event.preventDefault()

    const nextParams = buildSearchParams(searchValues)
    setSearchParams(nextParams)
    setSelectedRowKeys([])
    setCursorHistory([null])
    setNextCursor(null)
    setHasMore(false)
    await fetchAuditLogs(null, pageSize, nextParams, 1)
  }

  const handleClearSearch = async () => {
    setSearchValues({
      username: '',
      module: '',
      summary: '',
      method: 'all',
      status: 'all',
      ip_address: '',
      operation_type: '',
      log_level: 'all',
      start_time: '',
      end_time: '',
    })
    setSearchParams({})
    setSelectedRowKeys([])
    setCursorHistory([null])
    setNextCursor(null)
    setHasMore(false)
    await fetchAuditLogs(null, pageSize, {}, 1)
  }

  const handlePreviousPage = async () => {
    if (currentPage <= 1) return

    const targetPage = currentPage - 1
    const previousCursor = cursorHistory[targetPage - 1] || null
    setSelectedRowKeys([])
    await fetchAuditLogs(previousCursor, pageSize, searchParams, targetPage)
  }

  const handleNextPage = async () => {
    if (!nextCursor) return

    const targetPage = currentPage + 1
    setSelectedRowKeys([])
    setCursorHistory((previous) => {
      const nextHistory = previous.slice(0, currentPage)
      nextHistory.push(nextCursor)
      return nextHistory
    })
    await fetchAuditLogs(nextCursor, pageSize, searchParams, targetPage)
  }

  const handlePageSizeChange = async (value) => {
    const size = Number(value)
    setSelectedRowKeys([])
    setPageSize(size)
    setCursorHistory([null])
    setNextCursor(null)
    setHasMore(false)
    await fetchAuditLogs(null, size, searchParams, 1)
  }

  const openDetail = useCallback(async (record) => {
    setActiveLog(record)
    setDetailOpen(true)
    setDetailLoading(true)

    try {
      const response = await api.auditLogs.getDetail(record.id)
      setActiveLog(response.data || record)
    } catch (error) {
      handleBusinessError(error, '获取审计日志详情失败')
    } finally {
      setDetailLoading(false)
    }
  }, [handleBusinessError])

  const handleDelete = async () => {
    if (!deleteTarget) return

    try {
      await api.auditLogs.delete(deleteTarget.id)
      showSuccess('日志删除成功')
      setDeleteTarget(null)
      setSelectedRowKeys((previous) => previous.filter((key) => key !== deleteTarget.id))
      await refreshCurrentPage()
    } catch (error) {
      handleBusinessError(error, '日志删除失败')
    }
  }

  const handleBatchDelete = async () => {
    if (!selectedRowKeys.length) return

    try {
      await api.auditLogs.batchDelete(selectedRowKeys)
      showSuccess(`已删除 ${selectedRowKeys.length} 条日志`)
      setBatchDeleteVisible(false)
      setSelectedRowKeys([])
      await refreshCurrentPage()
    } catch (error) {
      handleBusinessError(error, '批量删除失败')
    }
  }

  const downloadExport = useCallback(async (filename, options = {}) => {
    const { silent = false } = options

    if (!filename) {
      if (!silent) showWarning('没有可下载的导出文件')
      return false
    }

    setDownloadLoading(true)
    try {
      const response = await api.auditLogs.download(filename)
      downloadBlobFile(response.data, filename)
      showSuccess('导出文件下载成功')
      return true
    } catch (error) {
      if (silent) {
        handleSilentError(error, '下载导出文件失败')
      } else {
        handleBusinessError(error, '下载导出文件失败')
      }
      return false
    } finally {
      setDownloadLoading(false)
    }
  }, [handleBusinessError, handleSilentError, showSuccess, showWarning])

  const handleExport = async () => {
    setExportLoading(true)
    try {
      const response = await api.auditLogs.export(searchParams)
      const exportFile = parseExportFileName(response.msg)

      showSuccess(response.msg || '导出任务已提交')
      if (!exportFile) return

      setLatestExportFile(exportFile)
      showInfo('导出文件生成中，系统会自动尝试下载')

      for (let attempt = 0; attempt < 6; attempt += 1) {
        await wait(1200)
        const isDownloaded = await downloadExport(exportFile, { silent: true })
        if (isDownloaded) return
      }

      showWarning(`导出文件仍在生成，可稍后点击“下载导出”重试：${exportFile}`)
    } catch (error) {
      handleBusinessError(error, '导出日志失败')
    } finally {
      setExportLoading(false)
    }
  }

  const handleSubmitClear = async () => {
    setClearLoading(true)
    try {
      const params = {}
      if (clearDays !== '') {
        params.days = Number(clearDays)
      }

      await api.auditLogs.clear(params)
      showSuccess(clearDays !== '' ? `已清理 ${clearDays} 天前的日志` : '已清空全部审计日志')
      setClearModalVisible(false)
      setClearDays('')
      setSelectedRowKeys([])
      setCursorHistory([null])
      setNextCursor(null)
      setHasMore(false)
      await fetchAuditLogs(null, pageSize, searchParams, 1)
    } catch (error) {
      handleBusinessError(error, '清理审计日志失败')
    } finally {
      setClearLoading(false)
    }
  }

  const handleCopyDetailContent = async (value, label) => {
    try {
      await navigator.clipboard.writeText(formatJsonBlock(value))
      showSuccess(`${label}已复制`)
    } catch (error) {
      handleSilentError(error, `${label}复制失败`)
      showWarning(`${label}复制失败`)
    }
  }

  const toggleSelectedRow = useCallback((id, checked) => {
    setSelectedRowKeys((current) =>
      checked ? (current.includes(id) ? current : [...current, id]) : current.filter((key) => key !== id),
    )
  }, [])

  const toggleSelectAllRows = useCallback((checked) => {
    setSelectedRowKeys(checked ? auditLogs.map((log) => log.id) : [])
  }, [auditLogs])

  const openDeleteDialog = useCallback((log) => {
    setDeleteTarget(log)
  }, [])

  const renderAuditTable = () => {
    if (!auditLogs.length) {
      return (
        <Empty className="border bg-muted/20 py-10">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileSearchIcon />
            </EmptyMedia>
            <EmptyTitle>暂无审计日志</EmptyTitle>
            <EmptyDescription>调整筛选条件后重试，或等待新的操作记录写入。</EmptyDescription>
          </EmptyHeader>
        </Empty>
      )
    }

    return (
      <>
        <div className="max-h-[60vh] overflow-auto rounded-lg border">
          <Table containerClassName="overflow-visible">
            <TableHeader>
              <TableRow>
                {isSuperuser ? (
                  <TableHead className="sticky top-0 z-10 w-12 bg-background shadow-[0_1px_0_hsl(var(--border))]">
                    <Checkbox
                      checked={allRowsSelected}
                      onCheckedChange={(checked) => toggleSelectAllRows(Boolean(checked))}
                    />
                  </TableHead>
                ) : null}
                <TableHead className="sticky top-0 z-10 bg-background shadow-[0_1px_0_hsl(var(--border))]">时间</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background shadow-[0_1px_0_hsl(var(--border))]">操作人</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background shadow-[0_1px_0_hsl(var(--border))]">模块 / 摘要</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background shadow-[0_1px_0_hsl(var(--border))]">请求</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background shadow-[0_1px_0_hsl(var(--border))]">结果</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background shadow-[0_1px_0_hsl(var(--border))]">性能 / 来源</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background text-right shadow-[0_1px_0_hsl(var(--border))]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {auditLogs.map((log) => (
                <AuditLogTableRow
                  key={log.id}
                  isSelected={selectedRowKeySet.has(log.id)}
                  isSuperuser={isSuperuser}
                  log={log}
                  onDelete={openDeleteDialog}
                  onOpenDetail={openDetail}
                  onToggleSelectedRow={toggleSelectedRow}
                />
              ))}
            </TableBody>
          </Table>
        </div>

        <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-muted-foreground">
            第 {currentPage} 页，本页 {auditLogs.length} 条，共 {total} 条
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">每页</span>
            <Select value={String(pageSize)} onValueChange={(value) => void handlePageSizeChange(value)}>
              <SelectTrigger className="w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {PAGE_SIZE_OPTIONS.map((value) => (
                    <SelectItem key={value} value={value}>
                      {value} 条
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <Button variant="outline" disabled={loading || currentPage <= 1} onClick={() => void handlePreviousPage()}>
              上一页
            </Button>
            <Button variant="outline" disabled={loading || !hasMore} onClick={() => void handleNextPage()}>
              下一页
            </Button>
          </div>
        </div>
      </>
    )
  }

  const renderDetailSheet = () => (
    <Sheet open={detailOpen} onOpenChange={setDetailOpen}>
      <SheetContent side="right" className="w-[min(56rem,100vw)] max-w-none overflow-hidden p-0">
        <SheetHeader className="sticky top-0 z-10 border-b bg-background/95 p-5 backdrop-blur">
          <SheetTitle>审计日志详情</SheetTitle>
          <SheetDescription>查看请求上下文、响应结果和客户端信息</SheetDescription>
        </SheetHeader>

        {detailLoading ? (
          <div className="p-5 text-sm text-muted-foreground">加载详情中...</div>
        ) : activeLog ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto p-5">
              <div className="flex flex-col gap-4">
                <Card size="sm">
                  <CardContent className="flex flex-col gap-4 pt-0">
                    <div className="flex flex-col gap-2 border-b pb-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={getMethodVariant(activeLog.method)}>{activeLog.method || '-'}</Badge>
                        <Badge variant={getStatusVariant(activeLog.status)}>{activeLog.status ?? '-'}</Badge>
                        <Badge variant={getLogLevelVariant(activeLog.log_level)}>{activeLog.log_level || '-'}</Badge>
                        <Badge variant="outline">{activeLog.response_time || 0} ms</Badge>
                      </div>
                      <div className="text-lg font-semibold leading-tight">
                        {activeLog.summary || activeLog.operation_type || '未命名操作'}
                      </div>
                      <code className="break-all rounded bg-muted px-3 py-2 text-xs">{activeLog.path || '-'}</code>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-[1fr_1fr_0.9fr]">
                      <DetailSection
                        title="基本信息"
                        className="border-t pt-4 first:border-t-0 first:pt-0 lg:border-t-0 lg:pt-0 lg:pr-5"
                      >
                        <DetailItem label="日志 ID">{activeLog.id}</DetailItem>
                        <DetailItem label="创建时间">{formatDateTime(activeLog.created_at)}</DetailItem>
                        <DetailItem label="操作人">{activeLog.username || 'system'}</DetailItem>
                        <DetailItem label="用户 ID">{activeLog.user_id || '-'}</DetailItem>
                      </DetailSection>

                      <DetailSection
                        title="请求信息"
                        className="border-t pt-4 lg:border-t-0 lg:border-l lg:pl-5 lg:pr-5"
                      >
                        <DetailItem label="模块">{activeLog.module || '基础模块'}</DetailItem>
                        <DetailItem label="操作类型">{activeLog.operation_type || '-'}</DetailItem>
                        <DetailItem label="请求方法">{activeLog.method || '-'}</DetailItem>
                        <DetailItem label="状态码">{activeLog.status ?? '-'}</DetailItem>
                      </DetailSection>

                      <DetailSection
                        title="客户端信息"
                        className="border-t pt-4 lg:border-t-0 lg:border-l lg:pl-5"
                      >
                        <DetailItem label="IP 地址">{activeLog.ip_address || '-'}</DetailItem>
                        <DetailItem label="日志级别">{activeLog.log_level || '-'}</DetailItem>
                        <DetailItem label="响应耗时">{activeLog.response_time || 0} ms</DetailItem>
                      </DetailSection>
                    </div>
                  </CardContent>
                </Card>

                <Tabs defaultValue="request_args" className="flex flex-col gap-4">
                  <TabsList variant="line" className="w-fit">
                    <TabsTrigger value="request_args">请求参数</TabsTrigger>
                    <TabsTrigger value="response_body">响应体</TabsTrigger>
                    <TabsTrigger value="user_agent">User-Agent</TabsTrigger>
                  </TabsList>
                  <TabsContent value="request_args" className="mt-0">
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <div className="text-sm text-muted-foreground">当前请求的入参快照</div>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon-sm"
                          onClick={() => void handleCopyDetailContent(activeLog.request_args, '请求参数')}
                        >
                          <CopyIcon />
                          <span className="sr-only">复制请求参数</span>
                        </Button>
                      </div>
                      <DetailCodeBlock value={activeLog.request_args} />
                    </div>
                  </TabsContent>
                  <TabsContent value="response_body" className="mt-0">
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <div className="text-sm text-muted-foreground">接口返回内容快照</div>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon-sm"
                          onClick={() => void handleCopyDetailContent(activeLog.response_body, '响应体')}
                        >
                          <CopyIcon />
                          <span className="sr-only">复制响应体</span>
                        </Button>
                      </div>
                      <DetailCodeBlock value={activeLog.response_body} />
                    </div>
                  </TabsContent>
                  <TabsContent value="user_agent" className="mt-0">
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <div className="text-sm text-muted-foreground">客户端 User-Agent 信息</div>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon-sm"
                          onClick={() => void handleCopyDetailContent(activeLog.user_agent || '暂无 User-Agent 信息', 'User-Agent')}
                        >
                          <CopyIcon />
                          <span className="sr-only">复制 User-Agent</span>
                        </Button>
                      </div>
                      <DetailCodeBlock value={activeLog.user_agent || '暂无 User-Agent 信息'} />
                    </div>
                  </TabsContent>
                </Tabs>
              </div>
            </div>
          </div>
        ) : (
          <Empty className="m-5 border bg-muted/20 py-8">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <InfoIcon />
              </EmptyMedia>
              <EmptyTitle>未选择日志记录</EmptyTitle>
            </EmptyHeader>
          </Empty>
        )}
      </SheetContent>
    </Sheet>
  )

  return (
    <div className="flex min-h-0 flex-col gap-5">
      <section className="flex flex-col gap-3 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">审计日志</h1>
          <p className="text-sm text-muted-foreground">查看系统操作记录、请求结果与上下文详情</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void handleExport()} disabled={exportLoading}>
            <DownloadIcon data-icon="inline-start" />
            {exportLoading ? '导出中...' : '导出日志'}
          </Button>
          <Button variant="outline" disabled={!latestExportFile || downloadLoading} onClick={() => void downloadExport(latestExportFile)}>
            <DownloadIcon data-icon="inline-start" />
            下载导出
          </Button>
          {isSuperuser ? (
            <Button variant="destructive" onClick={() => setClearModalVisible(true)}>
              <Trash2Icon data-icon="inline-start" />
              清理日志
            </Button>
          ) : null}
        </div>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
          <CardDescription>按操作人、模块、接口、状态和时间范围筛选日志</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSearch}>
            <FieldGroup className="grid gap-3 md:grid-cols-2 xl:grid-cols-[18rem_18rem_18rem_18rem] xl:items-end">
              <Field>
                <FieldLabel htmlFor="audit-username">操作人</FieldLabel>
                <Input
                  id="audit-username"
                  placeholder="例如 admin"
                  value={searchValues.username}
                  onChange={(event) => setSearchValues((current) => ({ ...current, username: event.target.value }))}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="audit-module">模块</FieldLabel>
                <Input
                  id="audit-module"
                  placeholder="例如 审计日志"
                  value={searchValues.module}
                  onChange={(event) => setSearchValues((current) => ({ ...current, module: event.target.value }))}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="audit-summary">接口摘要</FieldLabel>
                <Input
                  id="audit-summary"
                  placeholder="例如 查看审计日志"
                  value={searchValues.summary}
                  onChange={(event) => setSearchValues((current) => ({ ...current, summary: event.target.value }))}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="audit-ip-address">IP 地址</FieldLabel>
                <Input
                  id="audit-ip-address"
                  placeholder="例如 127.0.0.1"
                  value={searchValues.ip_address}
                  onChange={(event) => setSearchValues((current) => ({ ...current, ip_address: event.target.value }))}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="audit-operation-type">操作类型</FieldLabel>
                <Input
                  id="audit-operation-type"
                  placeholder="例如 删除"
                  value={searchValues.operation_type}
                  onChange={(event) => setSearchValues((current) => ({ ...current, operation_type: event.target.value }))}
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="audit-method">请求方法</FieldLabel>
                <Select value={searchValues.method} onValueChange={(value) => setSearchValues((current) => ({ ...current, method: value }))}>
                  <SelectTrigger id="audit-method" className="w-full">
                    <SelectValue placeholder="请求方法" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="all">全部方法</SelectItem>
                      {methodOptions.map((method) => (
                        <SelectItem key={method} value={method}>
                          {method}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>

              <Field>
                <FieldLabel htmlFor="audit-status">状态码</FieldLabel>
                <Select value={searchValues.status} onValueChange={(value) => setSearchValues((current) => ({ ...current, status: value }))}>
                  <SelectTrigger id="audit-status" className="w-full">
                    <SelectValue placeholder="状态码" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="all">全部状态码</SelectItem>
                      {statusOptions.map((status) => (
                        <SelectItem key={status} value={status}>
                          {status}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>

              <Field>
                <FieldLabel htmlFor="audit-log-level">日志级别</FieldLabel>
                <Select value={searchValues.log_level} onValueChange={(value) => setSearchValues((current) => ({ ...current, log_level: value }))}>
                  <SelectTrigger id="audit-log-level" className="w-full">
                    <SelectValue placeholder="日志级别" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="all">全部级别</SelectItem>
                      {logLevelOptions.map((level) => (
                        <SelectItem key={level} value={level}>
                          {level}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>

              <Field>
                <FieldLabel htmlFor="audit-start-time">开始时间</FieldLabel>
                <DateTimePicker
                  value={searchValues.start_time}
                  onChange={(nextValue) => setSearchValues((current) => ({ ...current, start_time: nextValue }))}
                  placeholder="选择开始时间"
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="audit-end-time">结束时间</FieldLabel>
                <DateTimePicker
                  value={searchValues.end_time}
                  onChange={(nextValue) => setSearchValues((current) => ({ ...current, end_time: nextValue }))}
                  placeholder="选择结束时间"
                />
              </Field>
            </FieldGroup>

            <div className="flex flex-wrap gap-2 xl:col-span-2 xl:items-end">
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

      <Card className="flex min-h-0 flex-1 flex-col">
        <CardHeader>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>审计记录</CardTitle>
              <CardDescription>第 {currentPage} 页，本页 {auditLogs.length} 条，共 {total} 条</CardDescription>
            </div>
            {isSuperuser ? (
              <div className="flex items-center gap-2">
                {selectedRowKeys.length > 0 ? (
                  <span className="text-sm text-muted-foreground">已选择 {selectedRowKeys.length} 条</span>
                ) : null}
                <Button
                  variant="destructive"
                  disabled={!selectedRowKeys.length}
                  onClick={() => setBatchDeleteVisible(true)}
                >
                  <Trash2Icon data-icon="inline-start" />
                  批量删除
                </Button>
              </div>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-col gap-4">{renderAuditTable()}</CardContent>
      </Card>

      {renderDetailSheet()}

      <Dialog open={clearModalVisible} onOpenChange={setClearModalVisible}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>清理审计日志</DialogTitle>
            <DialogDescription>留空表示清空全部日志。填写天数则表示只清理该天数之前的历史日志。</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="rounded-lg border bg-muted/20 p-3 text-sm text-muted-foreground">
              例如填写 30 表示清理 30 天前的数据。
            </div>
            <Field>
              <FieldLabel htmlFor="clear-days">清理多少天前的日志</FieldLabel>
              <Input
                id="clear-days"
                type="number"
                min="1"
                max="3650"
                placeholder="留空则清空全部"
                value={clearDays}
                onChange={(event) => setClearDays(event.target.value)}
              />
            </Field>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setClearModalVisible(false)}>
              取消
            </Button>
            <Button variant="destructive" disabled={clearLoading} onClick={() => void handleSubmitClear()}>
              {clearLoading ? '清理中...' : '执行清理'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        title="确认删除该日志？"
        description="删除后不可恢复，请谨慎操作。"
        confirmText="确认删除"
        destructive
        onConfirm={() => void handleDelete()}
      />

      <ConfirmDialog
        open={batchDeleteVisible}
        onOpenChange={setBatchDeleteVisible}
        title="确认批量删除选中日志？"
        description="删除后无法恢复，请谨慎操作。"
        confirmText="确认删除"
        destructive
        onConfirm={() => void handleBatchDelete()}
      />
    </div>
  )
}

export default AuditLog
