import { useEffect, useState } from 'react'
import { ApiOutlined, ApartmentOutlined, FileTextOutlined, ReloadOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons'
import { Button, Card, Col, Descriptions, Empty, Progress, Row, Space, Statistic, Table, Tag } from 'antd'

import api from '@/api'

const Dashboard = () => {
  const [loading, setLoading] = useState(false)
  const [overview, setOverview] = useState(null)

  useEffect(() => {
    let cancelled = false

    const loadOverview = async () => {
      setLoading(true)
      try {
        const response = await api.auth.getOverview()
        if (!cancelled) {
          setOverview(response.data || null)
        }
      } catch (error) {
        console.error('获取概览数据失败:', error)
        if (!cancelled) {
          setOverview(null)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadOverview()

    return () => {
      cancelled = true
    }
  }, [])

  const summary = overview?.summary || {}
  const system = overview?.system || {}
  const auditTrend = overview?.audit_trend || []
  const recentActivities = overview?.recent_activities || []
  const maxTrendCount = Math.max(...auditTrend.map((item) => item.count), 0)

  const statistics = [
    {
      key: 'users',
      title: '用户总数',
      value: summary.user_total || 0,
      icon: <UserOutlined />,
      color: '#1677ff',
      extra: `启用 ${summary.active_user_total || 0}`,
    },
    {
      key: 'roles',
      title: '角色数量',
      value: summary.role_total || 0,
      icon: <TeamOutlined />,
      color: '#52c41a',
      extra: '权限角色池',
    },
    {
      key: 'departments',
      title: '部门数量',
      value: summary.dept_total || 0,
      icon: <ApartmentOutlined />,
      color: '#13c2c2',
      extra: '组织结构节点',
    },
    {
      key: 'apis',
      title: 'API 数量',
      value: summary.api_total || 0,
      icon: <ApiOutlined />,
      color: '#722ed1',
      extra: '接口元数据',
    },
    {
      key: 'audits',
      title: '今日操作',
      value: summary.today_audit_total || 0,
      icon: <FileTextOutlined />,
      color: '#fa8c16',
      extra: '审计记录',
    },
  ]

  const activityColumns = [
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      render: (value) => value || 'system',
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      width: 140,
      render: (value) => value || '基础模块',
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => {
        const color = status >= 500 ? 'red' : status >= 400 ? 'orange' : 'green'
        return <Tag color={color}>{status}</Tag>
      },
    },
    {
      title: '耗时',
      dataIndex: 'response_time',
      key: 'response_time',
      width: 120,
      render: (value) => `${value || 0} ms`,
    },
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      width: 180,
    },
  ]

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-slate-900 via-blue-900 to-cyan-700 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">{system.title || '管理平台工作台'}</h1>
            <p className="text-white/80">
              当前环境 {system.environment || 'unknown'}，版本 {system.version || '0.0.0'}。工作台已切换为真实后端概览数据。
            </p>
          </div>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => window.location.reload()}>
              刷新页面
            </Button>
          </Space>
        </div>
      </div>

      <Row gutter={[16, 16]}>
        {statistics.map((item) => (
          <Col xs={24} sm={12} lg={8} xl={4} key={item.key}>
            <Card hoverable loading={loading} className="h-full">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-gray-500 text-sm mb-1">{item.title}</div>
                  <Statistic value={item.value} valueStyle={{ fontSize: 24, fontWeight: 700 }} />
                  <div className="text-xs text-gray-400 mt-2">{item.extra}</div>
                </div>
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center text-white text-xl shadow-sm"
                  style={{ backgroundColor: item.color }}
                >
                  {item.icon}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={10}>
          <Card title="框架状态" loading={loading} hoverable className="h-full">
            <Descriptions column={1} size="small" styles={{ label: { width: 160 } }}>
              <Descriptions.Item label="运行环境">
                <Tag color={system.environment === 'production' ? 'red' : 'blue'}>
                  {system.environment || 'unknown'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="数据库">{system.database || 'sqlite'}</Descriptions.Item>
              <Descriptions.Item label="访问日志">
                {system.access_log_enabled ? '已启用' : '已关闭'}
              </Descriptions.Item>
              <Descriptions.Item label="自动引导">
                {system.auto_bootstrap ? '已启用' : '已关闭'}
              </Descriptions.Item>
              <Descriptions.Item label="启动迁移">
                {system.auto_migration ? '自动升级' : '显式迁移'}
              </Descriptions.Item>
              <Descriptions.Item label="基础数据初始化">
                {system.auto_seed_data ? '自动初始化' : '手动初始化'}
              </Descriptions.Item>
              <Descriptions.Item label="API 元数据刷新">
                {system.auto_refresh_api ? '自动刷新' : '按需刷新'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} xl={14}>
          <Card title="近 7 天操作趋势" loading={loading} hoverable className="h-full">
            {auditTrend.length > 0 ? (
              <div className="space-y-4">
                {auditTrend.map((item) => (
                  <div key={item.date}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-600">{item.date}</span>
                      <span className="text-sm font-medium text-gray-800">{item.count} 次</span>
                    </div>
                    <Progress
                      percent={maxTrendCount > 0 ? Math.round((item.count / maxTrendCount) * 100) : 0}
                      showInfo={false}
                      strokeColor={{ from: '#1677ff', to: '#13c2c2' }}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="暂无审计趋势数据" />
            )}
          </Card>
        </Col>
      </Row>

      <Card title="最近操作" loading={loading} hoverable>
        <Table
          rowKey="id"
          columns={activityColumns}
          dataSource={recentActivities}
          pagination={{ pageSize: 8, hideOnSinglePage: true }}
          locale={{ emptyText: <Empty description="暂无操作记录" /> }}
          size="small"
          scroll={{ x: 900 }}
        />
      </Card>
    </div>
  )
}

export default Dashboard
