import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ApiOutlined,
  ClearOutlined,
  DeleteOutlined,
  EditOutlined,
  MenuOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyOutlined,
  SearchOutlined,
  UserOutlined,
} from '@ant-design/icons'
import {
  Button,
  Card,
  Empty,
  Form,
  Input,
  Modal,
  Pagination,
  Popconfirm,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
  Tree,
} from 'antd'

import api from '@/api'
import { useErrorHandler } from '@/hooks/useErrorHandler'

const { TextArea } = Input

const buildMenuTreeData = (menus = []) =>
  menus.map((menu) => ({
    key: menu.path,
    title: menu.name,
    children: buildMenuTreeData(menu.children || []),
  }))

const buildApiTreeData = (groups = []) =>
  groups.map((group) => ({
    key: `tag:${group.tag}`,
    title: `${group.tag} (${group.items?.length || 0})`,
    children: (group.items || []).map((item) => ({
      key: `api:${item.id}`,
      title: `${item.method} ${item.path} ${item.summary ? `- ${item.summary}` : ''}`,
      isLeaf: true,
    })),
  }))

const normalizeCheckedKeys = (checkedKeys) => {
  if (Array.isArray(checkedKeys)) {
    return checkedKeys
  }
  return checkedKeys?.checked || []
}

const RoleManagement = () => {
  const [loading, setLoading] = useState(false)
  const [roles, setRoles] = useState([])
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [searchForm] = Form.useForm()
  const [searchParams, setSearchParams] = useState({})

  const [permissionOptionsLoading, setPermissionOptionsLoading] = useState(false)
  const [permissionOptions, setPermissionOptions] = useState({ menu_tree: [], api_groups: [] })

  const [modalVisible, setModalVisible] = useState(false)
  const [modalForm] = Form.useForm()
  const [editingRole, setEditingRole] = useState(null)
  const [modalLoading, setModalLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [checkedMenuPaths, setCheckedMenuPaths] = useState([])
  const [checkedApiKeys, setCheckedApiKeys] = useState([])

  const { handleError, handleBusinessError, showSuccess } = useErrorHandler()

  const menuTreeData = useMemo(() => buildMenuTreeData(permissionOptions.menu_tree || []), [permissionOptions.menu_tree])
  const apiTreeData = useMemo(() => buildApiTreeData(permissionOptions.api_groups || []), [permissionOptions.api_groups])

  const fetchRoles = useCallback(
    async (page = 1, size = 10, search = {}) => {
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
    [handleError]
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
    void fetchRoles(1, 10, {})
    void fetchPermissionOptions()
  }, [fetchPermissionOptions, fetchRoles])

  const handleSearch = async (values) => {
    const params = {}
    if (values.role_name) {
      params.role_name = values.role_name
    }
    setSearchParams(params)
    setCurrentPage(1)
    await fetchRoles(1, pageSize, params)
  }

  const handleClearSearch = async () => {
    searchForm.resetFields()
    setSearchParams({})
    setCurrentPage(1)
    await fetchRoles(1, pageSize, {})
  }

  const handlePageChange = async (page, size) => {
    setCurrentPage(page)
    setPageSize(size)
    await fetchRoles(page, size, searchParams)
  }

  const handleCloseModal = useCallback(() => {
    setModalVisible(false)
    setEditingRole(null)
    setCheckedMenuPaths([])
    setCheckedApiKeys([])
    modalForm.resetFields()
  }, [modalForm])

  const handleOpenModal = async (role = null) => {
    setEditingRole(role)
    setModalVisible(true)
  }

  useEffect(() => {
    if (!modalVisible) {
      return
    }

    if (!permissionOptions.menu_tree?.length && !permissionOptionsLoading) {
      void fetchPermissionOptions()
    }

    if (!editingRole) {
      modalForm.resetFields()
      setCheckedMenuPaths([])
      setCheckedApiKeys([])
      setDetailLoading(false)
      return
    }

    let active = true

    const loadRoleDetail = async () => {
      setDetailLoading(true)
      try {
        const response = await api.roles.getById(editingRole.id)
        if (!active) {
          return
        }

        const detail = response.data || {}
        modalForm.setFieldsValue({
          name: detail.name || '',
          desc: detail.desc || '',
        })
        setCheckedMenuPaths(detail.menu_paths || [])
        setCheckedApiKeys((detail.api_ids || []).map((apiId) => `api:${apiId}`))
      } catch (error) {
        if (!active) {
          return
        }

        handleBusinessError(error, '获取角色详情失败')
        handleCloseModal()
      } finally {
        if (active) {
          setDetailLoading(false)
        }
      }
    }

    void loadRoleDetail()

    return () => {
      active = false
    }
  }, [
    editingRole,
    fetchPermissionOptions,
    handleBusinessError,
    handleCloseModal,
    modalForm,
    modalVisible,
    permissionOptions.menu_tree,
    permissionOptionsLoading,
  ])

  const handleSaveRole = async (values) => {
    setModalLoading(true)
    try {
      const payload = {
        ...values,
        menu_paths: checkedMenuPaths,
        api_ids: checkedApiKeys.map((key) => Number(String(key).replace('api:', ''))),
      }

      if (editingRole) {
        await api.roles.update({ ...payload, id: editingRole.id })
        showSuccess('角色更新成功')
      } else {
        await api.roles.create(payload)
        showSuccess('角色创建成功')
      }

      handleCloseModal()
      await fetchRoles(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, editingRole ? '角色更新失败' : '角色创建失败')
    } finally {
      setModalLoading(false)
    }
  }

  const handleDeleteRole = async (roleId) => {
    try {
      await api.roles.delete({ role_id: roleId })
      showSuccess('角色删除成功')
      await fetchRoles(currentPage, pageSize, searchParams)
    } catch (error) {
      handleBusinessError(error, '角色删除失败')
    }
  }

  const columns = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (text) => (
        <div className="flex items-center">
          <UserOutlined className="mr-2 text-blue-500" />
          <span className="font-medium">{text || '-'}</span>
        </div>
      ),
    },
    {
      title: '角色描述',
      dataIndex: 'desc',
      key: 'desc',
      width: 260,
      render: (text) => text || '-',
    },
    {
      title: '菜单权限',
      key: 'menu_count',
      width: 120,
      render: (_, record) => <Tag color="geekblue">{record.menu_count || 0} 项</Tag>,
    },
    {
      title: 'API权限',
      key: 'api_count',
      width: 120,
      render: (_, record) => <Tag color="purple">{record.api_count || 0} 项</Tag>,
    },
    {
      title: '用户数量',
      key: 'user_count',
      width: 120,
      render: (_, record) => <Tag color="blue">{record.user_count || 0} 人</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text) => (text ? new Date(text).toLocaleString('zh-CN') : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑角色与权限">
            <Button type="primary" size="small" icon={<EditOutlined />} onClick={() => void handleOpenModal(record)} />
          </Tooltip>

          <Tooltip title="删除">
            <Popconfirm
              title="确认删除角色？"
              description="删除后无法恢复，请谨慎操作"
              onConfirm={() => void handleDeleteRole(record.id)}
              okText="确认"
              cancelText="取消"
              okType="danger"
            >
              <Button danger size="small" icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">角色管理</h1>
          <p className="text-gray-500 mt-1">管理角色基础信息、菜单权限和 API 权限</p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => void handleOpenModal()}
          className="bg-gradient-to-r from-blue-500 to-blue-600"
        >
          新增角色
        </Button>
      </div>

      <Card className="shadow-sm">
        <div className="mb-6 pb-4 border-b border-gray-200">
          <div className="flex items-center mb-3">
            <SearchOutlined className="mr-2 text-blue-500" />
            <span className="font-medium text-gray-700">筛选条件</span>
          </div>
          <Form form={searchForm} layout="inline" onFinish={handleSearch} className="w-full">
            <Form.Item name="role_name" className="mb-2">
              <Input
                id="search_role_name"
                placeholder="角色名称"
                prefix={<UserOutlined />}
                allowClear
                style={{ width: 220 }}
              />
            </Form.Item>
            <Form.Item className="mb-2">
              <Space>
                <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading}>
                  搜索
                </Button>
                <Button icon={<ClearOutlined />} onClick={() => void handleClearSearch()}>
                  清空
                </Button>
                <Button icon={<ReloadOutlined />} onClick={() => void fetchRoles(currentPage, pageSize, searchParams)} loading={loading}>
                  刷新
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </div>

        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <SafetyOutlined className="mr-2 text-blue-500" />
              <span className="font-medium text-gray-700">角色列表</span>
            </div>
            <div className="text-sm text-gray-500">共 {total} 条记录</div>
          </div>

          <Table
            columns={columns}
            dataSource={roles}
            rowKey="id"
            loading={loading}
            pagination={false}
            scroll={{ x: 1200 }}
            size="middle"
            className="mb-4"
          />

          <div className="flex justify-center pt-4 border-t border-gray-200">
            <Pagination
              current={currentPage}
              pageSize={pageSize}
              total={total}
              showSizeChanger
              showQuickJumper
              showTotal={(count, range) => `第 ${range[0]}-${range[1]} 条，共 ${count} 条`}
              onChange={handlePageChange}
              pageSizeOptions={['10', '20', '50', '100']}
            />
          </div>
        </div>
      </Card>

      <Modal
        title={
          <div className="flex items-center">
            <SafetyOutlined className="mr-2 text-blue-500" />
            {editingRole ? '编辑角色权限' : '新增角色'}
          </div>
        }
        open={modalVisible}
        onCancel={handleCloseModal}
        footer={[
          <Button key="cancel" onClick={handleCloseModal}>
            取消
          </Button>,
          <Button key="submit" type="primary" loading={modalLoading} onClick={() => modalForm.submit()}>
            {editingRole ? '更新' : '创建'}
          </Button>,
        ]}
        width={960}
        destroyOnHidden
      >
        {detailLoading ? (
          <div className="py-16 flex items-center justify-center">
            <Spin />
          </div>
        ) : (
          <Form form={modalForm} layout="vertical" onFinish={handleSaveRole} className="mt-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card size="small" title="基础信息" className="lg:col-span-2">
                <Form.Item
                  label="角色名称"
                  name="name"
                  rules={[
                    { required: true, message: '请输入角色名称' },
                    { min: 2, max: 20, message: '角色名称长度为2-20个字符' },
                  ]}
                >
                  <Input id="modal_role_name" placeholder="请输入角色名称" autoComplete="off" />
                </Form.Item>

                <Form.Item
                  label="角色描述"
                  name="desc"
                  rules={[{ max: 500, message: '角色描述不能超过500个字符' }]}
                >
                  <TextArea
                    id="modal_role_desc"
                    placeholder="请输入角色描述"
                    rows={3}
                    showCount
                    maxLength={500}
                    autoComplete="off"
                  />
                </Form.Item>
              </Card>

              <Card
                size="small"
                title={
                  <span>
                    <MenuOutlined className="mr-2" />
                    菜单权限
                  </span>
                }
              >
                {permissionOptionsLoading ? (
                  <div className="py-12 flex items-center justify-center">
                    <Spin />
                  </div>
                ) : menuTreeData.length > 0 ? (
                  <Tree
                    checkable
                    defaultExpandAll
                    checkedKeys={checkedMenuPaths}
                    onCheck={(keys) => setCheckedMenuPaths(normalizeCheckedKeys(keys))}
                    treeData={menuTreeData}
                  />
                ) : (
                  <Empty description="暂无可授权菜单" />
                )}
              </Card>

              <Card
                size="small"
                title={
                  <span>
                    <ApiOutlined className="mr-2" />
                    API 权限
                  </span>
                }
                extra={<span className="text-xs text-gray-500">API 管理页独立维护资源目录</span>}
              >
                {permissionOptionsLoading ? (
                  <div className="py-12 flex items-center justify-center">
                    <Spin />
                  </div>
                ) : apiTreeData.length > 0 ? (
                  <Tree
                    checkable
                    defaultExpandAll
                    checkedKeys={checkedApiKeys}
                    onCheck={(keys) => {
                      const nextKeys = normalizeCheckedKeys(keys).filter((key) => String(key).startsWith('api:'))
                      setCheckedApiKeys(nextKeys)
                    }}
                    treeData={apiTreeData}
                  />
                ) : (
                  <Empty description="暂无可授权 API" />
                )}
              </Card>
            </div>
          </Form>
        )}
      </Modal>
    </div>
  )
}

export default RoleManagement
