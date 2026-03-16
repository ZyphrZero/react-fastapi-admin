import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ClearOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileSearchOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  SearchOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import {
  Button,
  Card,
  ConfigProvider,
  DatePicker,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Tooltip,
} from 'antd'
import dayjs from 'dayjs'

import api from '@/api'
import { useErrorHandler } from '@/hooks/useErrorHandler'
import { getStoredUserInfo } from '@/utils/session'

const { RangePicker } = DatePicker
const { TextArea } = Input

const DEFAULT_PAGE_SIZE = 100
const TABLE_SCROLL_X = 1560
const PAGE_SIZE_OPTIONS = [20, 50, 100, 200]
const RANGE_PICKER_DEFAULT_TIME = [
  dayjs().hour(0).minute(0).second(0).millisecond(0),
  dayjs().hour(23).minute(59).second(59).millisecond(0),
]

const methodOptions = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
  { label: 'PATCH', value: 'PATCH' },
]

const logLevelOptions = [
  { label: 'Info', value: 'info' },
  { label: 'Warning', value: 'warning' },
  { label: 'Error', value: 'error' },
]

const statusOptions = [
  { label: '200', value: 200 },
  { label: '201', value: 201 },
  { label: '400', value: 400 },
  { label: '401', value: 401 },
  { label: '403', value: 403 },
  { label: '404', value: 404 },
  { label: '422', value: 422 },
  { label: '500', value: 500 },
]

const getMethodColor = (method) => {
  const normalizedMethod = String(method || '').toUpperCase()

  if (normalizedMethod === 'GET') return 'green'
  if (normalizedMethod === 'POST') return 'blue'
  if (normalizedMethod === 'PUT') return 'orange'
  if (normalizedMethod === 'DELETE') return 'red'
  if (normalizedMethod === 'PATCH') return 'gold'
  return 'default'
}

const getStatusColor = (status) => {
  if (status >= 500) return 'red'
  if (status >= 400) return 'orange'
  if (status >= 300) return 'blue'
  if (status >= 200) return 'green'
  return 'default'
}

const getLogLevelColor = (level) => {
  const normalizedLevel = String(level || '').toLowerCase()

  if (normalizedLevel === 'error') return 'red'
  if (normalizedLevel === 'warning') return 'gold'
  if (normalizedLevel === 'info') return 'blue'
  return 'default'
}

const formatDateTime = (value) => {
  if (!value) {
    return '-'
  }

  return new Date(value).toLocaleString('zh-CN')
}

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

const buildSearchParams = (values = {}) => {
  const nextParams = {}

  if (values.username?.trim()) nextParams.username = values.username.trim()
  if (values.module?.trim()) nextParams.module = values.module.trim()
  if (values.summary?.trim()) nextParams.summary = values.summary.trim()
  if (values.method) nextParams.method = values.method
  if (typeof values.status === 'number') nextParams.status = values.status
  if (values.ip_address?.trim()) nextParams.ip_address = values.ip_address.trim()
  if (values.operation_type?.trim()) nextParams.operation_type = values.operation_type.trim()
  if (values.log_level) nextParams.log_level = values.log_level

  if (Array.isArray(values.time_range) && values.time_range.length === 2) {
    nextParams.start_time = values.time_range[0]?.format?.('YYYY-MM-DDTHH:mm:ss')
    nextParams.end_time = values.time_range[1]?.format?.('YYYY-MM-DDTHH:mm:ss')
  }

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

const shouldUpdateCellByRecord = (record, prevRecord) => record !== prevRecord

const auditTableTheme = {
  components: {
    Table: {
      rowSelectedBg: '#f5f5f5',
      rowSelectedHoverBg: '#eceff3',
    },
  },
}

const AuditLog = () => {
  const currentUser = getStoredUserInfo()
  const isSuperuser = Boolean(currentUser?.is_superuser)

  const [loading, setLoading] = useState(false)
  const [exportLoading, setExportLoading] = useState(false)
  const [downloadLoading, setDownloadLoading] = useState(false)
  const [clearLoading, setClearLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)

  const [auditLogs, setAuditLogs] = useState([])
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [hasMore, setHasMore] = useState(false)
  const [nextCursor, setNextCursor] = useState(null)
  const [cursorHistory, setCursorHistory] = useState([null])
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [searchParams, setSearchParams] = useState({})
  const [latestExportFile, setLatestExportFile] = useState('')

  const [detailOpen, setDetailOpen] = useState(false)
  const [activeLog, setActiveLog] = useState(null)
  const [clearModalVisible, setClearModalVisible] = useState(false)

  const [searchForm] = Form.useForm()
  const [clearForm] = Form.useForm()
  const detailRequestRef = useRef(0)

  const { handleError, handleBusinessError, handleSilentError, showInfo, showSuccess, showWarning } = useErrorHandler()

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
    [handleError]
  )

  useEffect(() => {
    void fetchAuditLogs(null, DEFAULT_PAGE_SIZE, {}, 1)
  }, [fetchAuditLogs])

  const handleSearch = async (values) => {
    const nextParams = buildSearchParams(values)

    setSearchParams(nextParams)
    setSelectedRowKeys([])
    setCursorHistory([null])
    setNextCursor(null)
    setHasMore(false)
    setCurrentPage(1)
    await fetchAuditLogs(null, pageSize, nextParams, 1)
  }

  const handleClearSearch = async () => {
    searchForm.resetFields()
    setSearchParams({})
    setSelectedRowKeys([])
    setCursorHistory([null])
    setNextCursor(null)
    setHasMore(false)
    setCurrentPage(1)
    await fetchAuditLogs(null, pageSize, {}, 1)
  }

  const handlePreviousPage = async () => {
    if (currentPage <= 1) {
      return
    }

    const targetPage = currentPage - 1
    const previousCursor = cursorHistory[targetPage - 1] || null

    setSelectedRowKeys([])
    await fetchAuditLogs(previousCursor, pageSize, searchParams, targetPage)
  }

  const handleNextPage = async () => {
    if (!nextCursor) {
      return
    }

    const targetPage = currentPage + 1

    setSelectedRowKeys([])
    setCursorHistory((previous) => {
      const nextHistory = previous.slice(0, currentPage)
      nextHistory.push(nextCursor)
      return nextHistory
    })
    await fetchAuditLogs(nextCursor, pageSize, searchParams, targetPage)
  }

  const handlePageSizeChange = async (size) => {
    setSelectedRowKeys([])
    setPageSize(size)
    setCursorHistory([null])
    setNextCursor(null)
    setHasMore(false)
    await fetchAuditLogs(null, size, searchParams, 1)
  }

  const handleRefresh = async () => {
    const currentCursor = cursorHistory[currentPage - 1] || null
    await fetchAuditLogs(currentCursor, pageSize, searchParams, currentPage)
  }

  const openDetail = useCallback(async (record) => {
    const currentRequestId = detailRequestRef.current + 1
    detailRequestRef.current = currentRequestId

    setActiveLog(record)
    setDetailOpen(true)
    setDetailLoading(true)

    try {
      const response = await api.auditLogs.getDetail(record.id)

      if (detailRequestRef.current !== currentRequestId) {
        return
      }

      setActiveLog(response.data || record)
    } catch (error) {
      if (detailRequestRef.current === currentRequestId) {
        handleBusinessError(error, '获取审计日志详情失败')
      }
    } finally {
      if (detailRequestRef.current === currentRequestId) {
        setDetailLoading(false)
      }
    }
  }, [handleBusinessError])

  const closeDetail = useCallback(() => {
    detailRequestRef.current += 1
    setDetailLoading(false)
    setDetailOpen(false)
    setActiveLog(null)
  }, [])

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

  const handleDelete = useCallback(async (id) => {
    try {
      await api.auditLogs.delete(id)
      showSuccess('日志删除成功')
      setSelectedRowKeys((previous) => previous.filter((key) => key !== id))
      await refreshCurrentPage()
    } catch (error) {
      handleBusinessError(error, '日志删除失败')
    }
  }, [handleBusinessError, refreshCurrentPage, showSuccess])

  const handleBatchDelete = async () => {
    if (!selectedRowKeys.length) {
      return
    }

    try {
      await api.auditLogs.batchDelete(selectedRowKeys)
      showSuccess(`已删除 ${selectedRowKeys.length} 条日志`)
      setSelectedRowKeys([])
      await refreshCurrentPage()
    } catch (error) {
      handleBusinessError(error, '批量删除失败')
    }
  }

  const downloadExportFile = useCallback(
    async (filename, options = {}) => {
      const { silent = false } = options

      if (!filename) {
        if (!silent) {
          showWarning('没有可下载的导出文件')
        }
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
    },
    [handleBusinessError, handleSilentError, showSuccess, showWarning]
  )

  const handleExport = async () => {
    setExportLoading(true)

    try {
      const response = await api.auditLogs.export(searchParams)
      const exportFile = parseExportFileName(response.msg)

      showSuccess(response.msg || '导出任务已提交')

      if (!exportFile) {
        return
      }

      setLatestExportFile(exportFile)
      showInfo('导出文件生成中，系统会自动尝试下载')

      for (let attempt = 0; attempt < 6; attempt += 1) {
        await wait(1200)
        const isDownloaded = await downloadExportFile(exportFile, { silent: true })

        if (isDownloaded) {
          return
        }
      }

      showWarning(`导出文件仍在生成，可稍后点击“下载最近导出”重试：${exportFile}`)
    } catch (error) {
      handleBusinessError(error, '导出日志失败')
    } finally {
      setExportLoading(false)
    }
  }

  const handleSubmitClear = async (values) => {
    setClearLoading(true)

    try {
      const params = {}
      if (typeof values.days === 'number') {
        params.days = values.days
      }

      await api.auditLogs.clear(params)
      showSuccess(typeof params.days === 'number' ? `已清理 ${params.days} 天前的日志` : '已清空全部审计日志')
      setClearModalVisible(false)
      clearForm.resetFields()
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

  const handleSelectionChange = useCallback((nextSelectedRowKeys) => {
    setSelectedRowKeys((previous) => {
      if (
        previous.length === nextSelectedRowKeys.length
        && previous.every((key, index) => key === nextSelectedRowKeys[index])
      ) {
        return previous
      }

      return nextSelectedRowKeys
    })
  }, [])

  const columns = useMemo(() => [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      shouldCellUpdate: shouldUpdateCellByRecord,
      render: (value) => (
        <div>
          <div className="font-medium text-slate-800">{formatDateTime(value)}</div>
          <div className="text-xs text-slate-400">日志时间点</div>
        </div>
      ),
    },
    {
      title: '操作人',
      key: 'operator',
      width: 160,
      shouldCellUpdate: shouldUpdateCellByRecord,
      render: (_, record) => (
        <div>
          <div className="font-medium text-slate-800">{record.username || 'system'}</div>
          <div className="text-xs text-slate-500">用户 ID: {record.user_id || '-'}</div>
        </div>
      ),
    },
    {
      title: '模块 / 摘要',
      key: 'module',
      width: 240,
      shouldCellUpdate: shouldUpdateCellByRecord,
      render: (_, record) => (
        <div className="space-y-1">
          <Tag color="geekblue">{record.module || '基础模块'}</Tag>
          <div className="text-sm text-slate-700 line-clamp-2" title={record.summary}>
            {record.summary || '-'}
          </div>
        </div>
      ),
    },
    {
      title: '请求',
      key: 'request',
      width: 320,
      shouldCellUpdate: shouldUpdateCellByRecord,
      render: (_, record) => (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Tag color={getMethodColor(record.method)} className="font-mono">
              {record.method || '-'}
            </Tag>
            <Tag color={getLogLevelColor(record.log_level)}>{record.log_level || 'unknown'}</Tag>
          </div>
          <div className="font-mono text-xs text-slate-700 break-all">{record.path || '-'}</div>
        </div>
      ),
    },
    {
      title: '结果',
      key: 'result',
      width: 180,
      shouldCellUpdate: shouldUpdateCellByRecord,
      render: (_, record) => (
        <div className="space-y-1">
          <Tag color={getStatusColor(record.status)}>{record.status ?? '-'}</Tag>
          <div className="text-xs text-slate-500">{record.operation_type || '未分类操作'}</div>
        </div>
      ),
    },
    {
      title: '性能 / 来源',
      key: 'meta',
      width: 200,
      shouldCellUpdate: shouldUpdateCellByRecord,
      render: (_, record) => (
        <div>
          <div className="font-medium text-slate-800">{record.response_time || 0} ms</div>
          <div className="text-xs text-slate-500">{record.ip_address || '-'}</div>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      fixed: 'right',
      shouldCellUpdate: shouldUpdateCellByRecord,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button type="primary" size="small" icon={<EyeOutlined />} onClick={() => void openDetail(record)} />
          </Tooltip>
          {isSuperuser ? (
            <Popconfirm
              title="确认删除该日志？"
              description="删除后不可恢复，请谨慎操作"
              onConfirm={() => handleDelete(record.id)}
              okText="确认"
              cancelText="取消"
              okType="danger"
            >
              <Button danger size="small" icon={<DeleteOutlined />} />
            </Popconfirm>
          ) : (
            <Tooltip title="仅超级管理员可删除日志">
              <span>
                <Button danger disabled size="small" icon={<DeleteOutlined />} />
              </span>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ], [handleDelete, isSuperuser, openDetail])

  const rowSelection = useMemo(() => ({
    selectedRowKeys,
    onChange: handleSelectionChange,
    preserveSelectedRowKeys: false,
    columnWidth: 52,
  }), [handleSelectionChange, selectedRowKeys])

  const shouldUseVirtualTable = auditLogs.length > 40
  const tableScroll = shouldUseVirtualTable ? { x: TABLE_SCROLL_X, y: 640 } : { x: TABLE_SCROLL_X }

  const detailTabItems = [
    {
      key: 'request_args',
      label: '请求参数',
      children: (
        <pre className="min-h-[180px] whitespace-pre-wrap break-all rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {formatJsonBlock(activeLog?.request_args)}
        </pre>
      ),
    },
    {
      key: 'response_body',
      label: '响应体',
      children: (
        <pre className="min-h-[180px] whitespace-pre-wrap break-all rounded-xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {formatJsonBlock(activeLog?.response_body)}
        </pre>
      ),
    },
    {
      key: 'user_agent',
      label: 'User-Agent',
      children: (
        <TextArea
          value={activeLog?.user_agent || '暂无 User-Agent 信息'}
          autoSize={{ minRows: 6, maxRows: 10 }}
          readOnly
          className="font-mono"
        />
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">审计日志</h1>
          <p className="mt-1 text-gray-500">查看系统操作记录、请求结果与上下文详情</p>
        </div>

        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={() => void handleRefresh()} loading={loading}>
            刷新
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => void handleExport()}
            loading={exportLoading}
          >
            导出日志
          </Button>
          <Button
            disabled={!latestExportFile}
            icon={<DownloadOutlined />}
            onClick={() => void downloadExportFile(latestExportFile, { silent: false })}
            loading={downloadLoading}
          >
            下载导出
          </Button>
          <Tooltip title={isSuperuser ? '清理历史审计日志' : '仅超级管理员可清理日志'}>
            <span>
              <Button
                danger
                disabled={!isSuperuser}
                icon={<DeleteOutlined />}
                onClick={() => setClearModalVisible(true)}
              >
                清理日志
              </Button>
            </span>
          </Tooltip>
        </Space>
      </div>

      <Card className="shadow-sm">
        <div className="mb-6 border-b border-slate-200 pb-4">
          <div className="mb-3 flex items-center">
            <SearchOutlined className="mr-2 text-blue-500" />
            <span className="font-medium text-slate-700">筛选条件</span>
          </div>

          <Form form={searchForm} layout="inline" onFinish={handleSearch} className="w-full gap-y-2">
            <Form.Item name="username" className="mb-3">
              <Input placeholder="操作人" allowClear style={{ width: 160 }} />
            </Form.Item>
            <Form.Item name="module" className="mb-3">
              <Input placeholder="模块" allowClear style={{ width: 160 }} />
            </Form.Item>
            <Form.Item name="summary" className="mb-3">
              <Input placeholder="接口摘要" allowClear style={{ width: 180 }} />
            </Form.Item>
            <Form.Item name="method" className="mb-3">
              <Select placeholder="请求方法" allowClear options={methodOptions} style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="status" className="mb-3">
              <Select placeholder="状态码" allowClear options={statusOptions} style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="log_level" className="mb-3">
              <Select placeholder="日志级别" allowClear options={logLevelOptions} style={{ width: 140 }} />
            </Form.Item>
            <Form.Item name="ip_address" className="mb-3">
              <Input placeholder="IP 地址" allowClear style={{ width: 160 }} />
            </Form.Item>
            <Form.Item name="operation_type" className="mb-3">
              <Input placeholder="操作类型" allowClear style={{ width: 160 }} />
            </Form.Item>
            <Form.Item name="time_range" className="mb-3">
              <RangePicker showTime={{ defaultOpenValue: RANGE_PICKER_DEFAULT_TIME }} />
            </Form.Item>
            <Form.Item className="mb-3">
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SearchOutlined />}
                  loading={loading}
                >
                  搜索
                </Button>
                <Button icon={<ClearOutlined />} onClick={() => void handleClearSearch()}>
                  清空
                </Button>
                <Button icon={<ReloadOutlined />} onClick={() => void handleRefresh()} loading={loading}>
                  刷新
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </div>

        <div>
          <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center">
              <FileSearchOutlined className="mr-2 text-blue-500" />
              <span className="font-medium text-slate-700">审计记录</span>
              <span className="ml-3 text-sm text-slate-500">第 {currentPage} 页，本页 {auditLogs.length} 条</span>
            </div>

            <Space wrap>
              {selectedRowKeys.length > 0 ? (
                <span className="text-sm text-slate-500">已选择 {selectedRowKeys.length} 条</span>
              ) : null}
              {isSuperuser ? (
                <Popconfirm
                  title="确认批量删除选中日志？"
                  description="删除后无法恢复，请谨慎操作"
                  onConfirm={() => void handleBatchDelete()}
                  okText="确认"
                  cancelText="取消"
                  okType="danger"
                  disabled={!selectedRowKeys.length}
                >
                  <Button
                    danger
                    disabled={!selectedRowKeys.length}
                    icon={<DeleteOutlined />}
                  >
                    批量删除
                  </Button>
                </Popconfirm>
              ) : (
                <Tooltip title="仅超级管理员可批量删除">
                  <span>
                    <Button danger disabled icon={<DeleteOutlined />}>
                      批量删除
                    </Button>
                  </span>
                </Tooltip>
              )}
            </Space>
          </div>

          <ConfigProvider theme={auditTableTheme}>
            <Table
              rowKey="id"
              columns={columns}
              dataSource={auditLogs}
              rowSelection={isSuperuser ? rowSelection : undefined}
              loading={loading}
              pagination={false}
              virtual={shouldUseVirtualTable}
              scroll={tableScroll}
              size="middle"
              className="mb-4"
              locale={{ emptyText: <Empty description="暂无审计日志" /> }}
              onRow={(record) => ({
                onDoubleClick: () => void openDetail(record),
              })}
            />
          </ConfigProvider>

          <div className="flex flex-col gap-3 border-t border-slate-200 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm text-slate-500">
              当前第 {currentPage} 页，{hasMore ? '还有更多记录' : '已到最后一页'}
            </div>

            <Space wrap>
              <span className="text-sm text-slate-500">每页</span>
              <Select
                value={pageSize}
                options={PAGE_SIZE_OPTIONS.map((value) => ({ label: `${value} 条`, value }))}
                style={{ width: 110 }}
                onChange={(value) => void handlePageSizeChange(value)}
              />
              <Button disabled={loading || currentPage <= 1} onClick={() => void handlePreviousPage()}>
                上一页
              </Button>
              <Button type="primary" disabled={loading || !hasMore} onClick={() => void handleNextPage()}>
                下一页
              </Button>
            </Space>
          </div>
        </div>
      </Card>

      <Drawer
        title={
          <div className="flex items-center">
            <InfoCircleOutlined className="mr-2 text-blue-500" />
            审计日志详情
          </div>
        }
        open={detailOpen}
        size="large"
        onClose={closeDetail}
      >
        <Spin spinning={detailLoading}>
          {activeLog ? (
            <div className="space-y-6">
              <Card size="small" className="overflow-hidden border-none bg-slate-50 shadow-none">
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="日志 ID">{activeLog.id}</Descriptions.Item>
                  <Descriptions.Item label="创建时间">{formatDateTime(activeLog.created_at)}</Descriptions.Item>
                  <Descriptions.Item label="操作人">{activeLog.username || 'system'}</Descriptions.Item>
                  <Descriptions.Item label="用户 ID">{activeLog.user_id || '-'}</Descriptions.Item>
                  <Descriptions.Item label="模块">{activeLog.module || '基础模块'}</Descriptions.Item>
                  <Descriptions.Item label="操作类型">{activeLog.operation_type || '-'}</Descriptions.Item>
                  <Descriptions.Item label="请求方法">
                    <Tag color={getMethodColor(activeLog.method)}>{activeLog.method || '-'}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="日志级别">
                    <Tag color={getLogLevelColor(activeLog.log_level)}>{activeLog.log_level || '-'}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="状态码">
                    <Tag color={getStatusColor(activeLog.status)}>{activeLog.status ?? '-'}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="响应耗时">{activeLog.response_time || 0} ms</Descriptions.Item>
                  <Descriptions.Item label="IP 地址" span={2}>
                    {activeLog.ip_address || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="请求路径" span={2}>
                    <div className="font-mono break-all text-xs text-slate-700">{activeLog.path || '-'}</div>
                  </Descriptions.Item>
                  <Descriptions.Item label="摘要" span={2}>
                    {activeLog.summary || '-'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>

              <Tabs items={detailTabItems} />
            </div>
          ) : (
            <Empty description="未选择日志记录" />
          )}
        </Spin>
      </Drawer>

      <Modal
        title={
          <div className="flex items-center">
            <WarningOutlined className="mr-2 text-orange-500" />
            清理审计日志
          </div>
        }
        open={clearModalVisible}
        onCancel={() => {
          setClearModalVisible(false)
          clearForm.resetFields()
        }}
        onOk={() => clearForm.submit()}
        okText="执行清理"
        okButtonProps={{ danger: true, loading: clearLoading }}
        cancelText="取消"
        destroyOnHidden
      >
        <Form form={clearForm} layout="vertical" onFinish={handleSubmitClear} className="mt-4">
          <div className="mb-4 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm leading-6 text-orange-700">
            留空表示清空全部日志。填写天数则表示只清理该天数之前的历史日志，例如填写 30 表示清理 30 天前的数据。
          </div>

          <Form.Item label="清理多少天前的日志" name="days">
            <InputNumber min={1} max={3650} className="w-full" placeholder="留空则清空全部" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AuditLog
