import { useCallback, useEffect, useState } from 'react'
import {
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Card,
  Row,
  Col,
  Tag,
  Popconfirm,
  Pagination,
  Tooltip,
  Select
} from 'antd'
import {
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  ClearOutlined,
  ApiOutlined,
  SyncOutlined,
  QuestionCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'
import api from '@/api'
import { useErrorHandler } from '@/hooks/useErrorHandler'

const { TextArea } = Input
const { Option } = Select

const ApiManagement = () => {
  // 基础状态
  const [loading, setLoading] = useState(false)
  const [apis, setApis] = useState([])
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  
  // 搜索状态
  const [searchForm] = Form.useForm()
  const [searchParams, setSearchParams] = useState({})
  const [availableTags, setAvailableTags] = useState([])
  
  // 模态框状态
  const [modalVisible, setModalVisible] = useState(false)
  const [modalForm] = Form.useForm()
  const [editingApi, setEditingApi] = useState(null)
  const [modalLoading, setModalLoading] = useState(false)
  
  // 刷新状态
  const [refreshLoading, setRefreshLoading] = useState(false)
  
  const { handleError, handleBusinessError, showSuccess } = useErrorHandler()

  // HTTP方法选项
  const httpMethods = [
    { label: 'GET', value: 'GET', color: 'green' },
    { label: 'POST', value: 'POST', color: 'blue' },
    { label: 'PUT', value: 'PUT', color: 'orange' },
    { label: 'DELETE', value: 'DELETE', color: 'red' },
    { label: 'PATCH', value: 'PATCH', color: 'purple' }
  ]

  // 获取API列表
  const fetchApis = useCallback(async (page = 1, size = 10, search = {}) => {
    setLoading(true)
    try {
      const params = {
        page,
        page_size: size,
        ...search
      }
      const response = await api.apis.getList(params)
      const apiList = response.data || []
      setApis(apiList)
      setTotal(response.total || 0)
      setCurrentPage(response.page || page)
      setPageSize(response.page_size || size)
    } catch (error) {
      handleError(error, '获取API列表失败')
    } finally {
      setLoading(false)
    }
  }, [handleError])

  // 获取所有API标签
  const fetchAllTags = useCallback(async () => {
    try {
      const response = await api.apis.getTags()
      setAvailableTags(
        (response.data || []).map((tag) => ({
          label: tag,
          value: tag,
          count: 0,
        }))
      )
    } catch (error) {
      handleError(error, '获取API标签失败')
    }
  }, [handleError])

  // 初始化数据
  useEffect(() => {
    void fetchApis(1, 10, {})
    void fetchAllTags()
  }, [fetchAllTags, fetchApis])

  useEffect(() => {
    if (!modalVisible || !editingApi) {
      return
    }

    modalForm.setFieldsValue({
      id: editingApi.id,
      path: editingApi.path || '',
      method: editingApi.method || 'GET',
      summary: editingApi.summary || '',
      tags: editingApi.tags || '',
    })
  }, [editingApi, modalForm, modalVisible])

  // 搜索处理
  const handleSearch = async (values) => {
    const params = {}
    if (values.path) params.path = values.path
    if (values.summary) params.summary = values.summary
    if (values.tags && values.tags.length > 0) {
      // 多标签筛选：将数组转换为逗号分隔的字符串
      params.tags = Array.isArray(values.tags) ? values.tags.join(',') : values.tags
    }

    setSearchParams(params)
    setCurrentPage(1)
    await fetchApis(1, pageSize, params)
  }

  // 清空搜索
  const handleClearSearch = async () => {
    searchForm.resetFields()
    setSearchParams({})
    setCurrentPage(1)
    await fetchApis(1, pageSize, {})
  }

  // 分页处理
  const handlePageChange = async (page, size) => {
    setCurrentPage(page)
    setPageSize(size)
    await fetchApis(page, size, searchParams)
  }

  // 打开编辑模态框
  const handleOpenModal = (apiItem) => {
    if (!apiItem) return // 只允许编辑，不允许创建

    setEditingApi(apiItem)
    setModalVisible(true)
  }

  // 关闭模态框
  const handleCloseModal = () => {
    setModalVisible(false)
    setEditingApi(null)
    modalForm.resetFields()
  }

  // 保存API
  const handleSaveApi = async (values) => {
    if (!editingApi) return // 只允许更新，不允许创建

    setModalLoading(true)
    try {
      // 更新API - 只允许更新描述和标签
      await api.apis.update({
        ...values,
        id: editingApi.id,
        path: editingApi.path, // 保持原路径不变
        method: editingApi.method // 保持原方法不变
      })
      showSuccess('API信息更新成功')

      handleCloseModal()
      await fetchApis(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, 'API更新失败')
    } finally {
      setModalLoading(false)
    }
  }

  // 删除API
  const handleDeleteApi = async (apiId) => {
    try {
      await api.apis.delete({ api_id: apiId })
      showSuccess('API删除成功')
      await fetchApis(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, 'API删除失败')
    }
  }

  // 刷新API列表
  const handleRefreshApis = async () => {
    setRefreshLoading(true)
    try {
      await api.apis.refresh()
      showSuccess('API列表刷新成功')
      await fetchApis(currentPage, pageSize, searchParams)
      await fetchAllTags() // 刷新后重新获取标签列表
    } catch (error) {
      handleBusinessError(error, 'API刷新失败')
    } finally {
      setRefreshLoading(false)
    }
  }

  // 获取方法颜色
  const getMethodColor = (method) => {
    const methodObj = httpMethods.find(m => m.value === method)
    return methodObj ? methodObj.color : 'default'
  }



  // 表格列定义
  const columns = [
    {
      title: 'API信息',
      key: 'api_info',
      width: 350,
      render: (_, record) => (
        <div className="space-y-2">
          <div className="flex items-center">
            <Tag color={getMethodColor(record.method)} className="font-mono mr-2">
              {record.method}
            </Tag>
            <code className="bg-gray-100 px-2 py-1 rounded text-sm flex-1">
              {record.path || '-'}
            </code>
          </div>

        </div>
      )
    },
    {
      title: 'API描述',
      dataIndex: 'summary',
      key: 'summary',
      width: 250,
      render: (text) => (
        <div className="max-w-xs">
          <div className="truncate" title={text}>
            {text || '-'}
          </div>
        </div>
      )
    },
    {
      title: 'API标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 120,
      render: (tags) => (
        <Tag color="cyan">{tags || '未分类'}</Tag>
      )
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: () => (
        <div className="space-y-1">
          <Tag color="green" className="text-xs">
            已同步
          </Tag>
        </div>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (text) => text ? new Date(text).toLocaleString('zh-CN') : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑API">
            <Button
              type="primary"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleOpenModal(record)}
            />
          </Tooltip>
          <Tooltip title="删除API">
            <Popconfirm
              title="确认删除API？"
              description="删除后无法恢复"
              onConfirm={() => handleDeleteApi(record.id)}
              okText="确认"
              cancelText="取消"
              okType="danger"
            >
              <Button
                danger
                size="small"
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      )
    }
  ]

  return (
    <div className="space-y-4">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-gray-800">API管理</h1>
            <Tooltip
              title={
                <div className="text-sm max-w-sm">
                  <div className="font-medium mb-2">API管理说明：</div>
                  <div className="mb-1">• 系统自动扫描所有API接口，无需手动创建</div>
                  <div className="mb-1">• 只能编辑API描述和标签，路径和方法不可修改</div>
                  <div>• 代码更新后，重新扫描即可同步最新API</div>
                </div>
              }
              placement="right"
            >
              <QuestionCircleOutlined className="ml-2 text-gray-400 hover:text-blue-500 cursor-help text-base" />
            </Tooltip>
          </div>
          <p className="text-gray-500 mt-1">自动管理系统API接口，扫描代码同步接口信息，无需手动维护</p>
        </div>
        <Space>
          <Button
            type="primary"
            icon={<SyncOutlined spin={refreshLoading} />}
            onClick={handleRefreshApis}
            loading={refreshLoading}
            className="bg-gradient-to-r from-green-500 to-green-600"
          >
            {refreshLoading ? '扫描中...' : '扫描系统API'}
          </Button>
        </Space>
      </div>

      {/* API管理主卡片 */}
      <Card className="shadow-sm">
        {/* 搜索表单 */}
        <div className="mb-6 pb-4 border-b border-gray-200">
          <div className="flex items-center mb-3">
            <SearchOutlined className="mr-2 text-blue-500" />
            <span className="font-medium text-gray-700">筛选条件</span>
          </div>
          <Form
            form={searchForm}
            layout="inline"
            onFinish={handleSearch}
            className="w-full"
          >
                         <Form.Item name="path" className="mb-2">
               <Input
                 id="search_api_path"
                 placeholder="API路径"
                 prefix={<ApiOutlined />}
                 allowClear
                 style={{ width: 200 }}
               />
             </Form.Item>
             <Form.Item name="summary" className="mb-2">
               <Input
                 id="search_api_summary"
                 placeholder="API描述"
                 allowClear
                 style={{ width: 180 }}
               />
             </Form.Item>
             <Form.Item name="tags" className="mb-2">
               <Select
                 id="search_api_tags"
                 mode="multiple"
                 placeholder={`选择标签 (${availableTags.length}个)`}
                 allowClear
                 showSearch
                 filterOption={(input, option) => {
                   const tagLabel = option?.label || '';
                   return tagLabel.toLowerCase().includes(input.toLowerCase());
                 }}
                 style={{ width: 200 }}
                 popupMatchSelectWidth={false}
                 listHeight={200}
                 notFoundContent="未找到匹配的标签"
                 maxTagCount={2}
                 maxTagPlaceholder={(omittedValues) => `+${omittedValues.length}个标签`}
               >
                 {availableTags.map(tag => (
                   <Option key={tag.value} value={tag.value} label={tag.label}>
                     <Tag color="cyan" size="small">{tag.label}</Tag>
                   </Option>
                 ))}
               </Select>
             </Form.Item>
            <Form.Item className="mb-2">
              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SearchOutlined />}
                  loading={loading}
                >
                  搜索
                </Button>
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleClearSearch}
                >
                  清空
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => fetchApis(currentPage, pageSize, searchParams)}
                  loading={loading}
                >
                  刷新
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </div>

        {/* API列表 */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <ApiOutlined className="mr-2 text-blue-500" />
              <span className="font-medium text-gray-700">API列表</span>
            </div>
            <div className="text-sm text-gray-500">
              共 {total} 条记录
            </div>
          </div>
          
          <Table
            columns={columns}
            dataSource={apis}
            rowKey="id"
            loading={loading}
            pagination={false}
            scroll={{ x: 1000 }}
            size="middle"
            className="mb-4"
          />
          
          {/* 分页 */}
          <div className="flex justify-center pt-4 border-t border-gray-200">
            <Pagination
              current={currentPage}
              pageSize={pageSize}
              total={total}
              showSizeChanger
              showQuickJumper
              showTotal={(total, range) => 
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
              }
              onChange={handlePageChange}
              pageSizeOptions={['10', '20', '50', '100']}
            />
          </div>
        </div>
      </Card>

      {/* 编辑API模态框 */}
      <Modal
        title={
          <div className="flex items-center">
            <ApiOutlined className="mr-2 text-blue-500" />
            编辑API信息
          </div>
        }
        open={modalVisible}
        onCancel={handleCloseModal}
        footer={[
          <Button key="cancel" onClick={handleCloseModal}>
            取消
          </Button>,
          <Button
            key="submit"
            type="primary"
            loading={modalLoading}
            onClick={() => modalForm.submit()}
          >
            {editingApi ? '更新' : '创建'}
          </Button>
        ]}
        width={600}
        destroyOnHidden
      >
        <Form
          form={modalForm}
          layout="vertical"
          onFinish={handleSaveApi}
          className="mt-4"
        >
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item
                label="API路径"
                name="path"
              >
                <Input
                  id="modal_api_path"
                  disabled
                  className="bg-gray-50"
                />
              </Form.Item>
               </Col>
               <Col span={8}>
              <Form.Item
                label="请求方法"
                name="method"
              >
                <Select
                  id="modal_api_method"
                  disabled
                  className="bg-gray-50"
                >
                  {httpMethods.map(method => (
                    <Option key={method.value} value={method.value}>
                      <Tag color={method.color}>{method.label}</Tag>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded">
            <div className="text-sm text-blue-600">
              <strong>说明：</strong>API路径和方法由系统自动扫描生成，不可修改。您只能编辑API的描述和标签信息。
            </div>
          </div>

          <Form.Item
             label="API描述"
             name="summary"
             rules={[
               { required: true, message: '请输入API描述' },
               { max: 500, message: 'API描述不能超过500个字符' }
             ]}
           >
             <Input 
               id="modal_api_summary"
               placeholder="请输入API功能描述" 
             />
           </Form.Item>
           
           <Form.Item
             label="API标签"
             name="tags"
             rules={[
               { required: true, message: '请输入API标签' },
               { max: 100, message: 'API标签不能超过100个字符' }
             ]}
           >
             <Input 
               id="modal_api_tags"
               placeholder="例如: User, Role, System" 
             />
           </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ApiManagement 
