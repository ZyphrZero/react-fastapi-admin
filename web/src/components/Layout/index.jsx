import { useEffect, useState } from 'react'
import { Avatar, Breadcrumb, Button, Dropdown, Layout, Menu, Space, Spin, Tabs, theme } from 'antd'
import { LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined, UserOutlined } from '@ant-design/icons'
import { Icon } from '@iconify/react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

import api from '@/api'
import { clearSession, getStoredUserInfo, subscribeSessionChange } from '@/utils/session'

const { Header, Sider, Content } = Layout

const DEFAULT_TAB = {
  key: '/dashboard',
  label: '工作台',
  closable: false,
}

const mapMenuTreeToItems = (menus = []) =>
  menus
    .filter((menu) => !menu.is_hidden)
    .sort((left, right) => (left.order || 0) - (right.order || 0))
    .map((menu) => {
      const children = mapMenuTreeToItems(menu.children || [])

      return {
        key: menu.path,
        label: menu.name,
        redirect: menu.redirect,
        icon: menu.icon ? <Icon icon={menu.icon} width="16" height="16" /> : null,
        children: children.length > 0 ? children : undefined,
      }
    })

const buildLabelMap = (items, labelMap = {}) => {
  items.forEach((item) => {
    labelMap[item.key] = item.label
    if (item.children?.length) {
      buildLabelMap(item.children, labelMap)
    }
  })

  return labelMap
}

const findMenuItem = (items, targetKey) => {
  for (const item of items) {
    if (item.key === targetKey) {
      return item
    }

    if (item.children?.length) {
      const child = findMenuItem(item.children, targetKey)
      if (child) {
        return child
      }
    }
  }

  return null
}

const findOpenKeys = (items, targetKey, parentKeys = []) => {
  for (const item of items) {
    if (item.key === targetKey) {
      return parentKeys
    }

    if (item.children?.length) {
      const childKeys = findOpenKeys(item.children, targetKey, [...parentKeys, item.key])
      if (childKeys.length > 0) {
        return childKeys
      }
    }
  }

  return []
}

const AppLayout = () => {
  const [collapsed, setCollapsed] = useState(false)
  const [userInfo, setUserInfo] = useState(() => getStoredUserInfo())
  const [menuItems, setMenuItems] = useState([])
  const [menuLoading, setMenuLoading] = useState(false)
  const [openKeys, setOpenKeys] = useState([])
  const [tabs, setTabs] = useState([DEFAULT_TAB])
  const [activeTab, setActiveTab] = useState('/dashboard')
  const navigate = useNavigate()
  const location = useLocation()
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken()

  const breadcrumbNameMap = {
    '/profile': '个人中心',
    ...buildLabelMap(menuItems),
  }

  const resolveTabLabel = (path) => breadcrumbNameMap[path] || path

  const addTab = (path, label = resolveTabLabel(path)) => {
    setTabs((previousTabs) => {
      if (previousTabs.some((tab) => tab.key === path)) {
        return previousTabs
      }

      return [...previousTabs, { key: path, label, closable: path !== '/dashboard' }]
    })

    setActiveTab(path)
    navigate(path)
  }

  const removeTab = (targetKey) => {
    if (targetKey === '/dashboard') {
      return
    }

    const nextTabs = tabs.filter((tab) => tab.key !== targetKey)
    setTabs(nextTabs)

    if (activeTab === targetKey && nextTabs.length > 0) {
      const fallbackTab = nextTabs[nextTabs.length - 1]
      setActiveTab(fallbackTab.key)
      navigate(fallbackTab.key)
    }
  }

  const handleTabChange = (key) => {
    setActiveTab(key)
    navigate(key)
  }

  const handleLogout = () => {
    clearSession()
    setUserInfo(null)
    setTabs([DEFAULT_TAB])
    setActiveTab('/dashboard')
    navigate('/login')
  }

  useEffect(() => {
    let cancelled = false

    const loadMenus = async () => {
      setMenuLoading(true)
      try {
        const response = await api.auth.getUserMenu()
        if (!cancelled) {
          setMenuItems(mapMenuTreeToItems(response.data || []))
        }
      } catch (error) {
        console.error('获取菜单失败:', error)
        if (!cancelled) {
          setMenuItems([])
        }
      } finally {
        if (!cancelled) {
          setMenuLoading(false)
        }
      }
    }

    loadMenus()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const handleSessionChange = () => {
      setUserInfo(getStoredUserInfo())
    }

    handleSessionChange()
    return subscribeSessionChange(handleSessionChange)
  }, [])

  useEffect(() => {
    const currentPath = location.pathname
    const currentLabelMap = {
      '/profile': '个人中心',
      ...buildLabelMap(menuItems),
    }
    const label = currentLabelMap[currentPath] || currentPath

    setActiveTab(currentPath)
    setTabs((previousTabs) => {
      const currentTab = previousTabs.find((tab) => tab.key === currentPath)

      if (!currentTab) {
        return [...previousTabs, { key: currentPath, label, closable: currentPath !== '/dashboard' }]
      }

      if (currentTab.label === label) {
        return previousTabs
      }

      return previousTabs.map((tab) => (tab.key === currentPath ? { ...tab, label } : tab))
    })
  }, [location.pathname, menuItems])

  useEffect(() => {
    setOpenKeys(findOpenKeys(menuItems, location.pathname))
  }, [location.pathname, menuItems])

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined className="text-blue-500" />,
      label: (
        <div className="flex flex-col">
          <span className="font-medium">个人中心</span>
          <span className="text-xs text-gray-500">查看和编辑个人信息</span>
        </div>
      ),
      onClick: () => addTab('/profile', '个人中心'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined className="text-red-500" />,
      label: (
        <div className="flex flex-col">
          <span className="font-medium text-red-600">退出登录</span>
          <span className="text-xs text-gray-500">安全退出系统</span>
        </div>
      ),
      onClick: handleLogout,
    },
  ]

  const breadcrumbItems = location.pathname
    .split('/')
    .filter(Boolean)
    .map((_, index, pathSnippets) => {
      const url = `/${pathSnippets.slice(0, index + 1).join('/')}`
      return {
        title: breadcrumbNameMap[url] || url,
      }
    })

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        className="shadow-lg"
        theme="light"
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div className="h-14 flex items-center justify-center border-b border-gray-100 bg-gray-50/50">
          {collapsed ? (
            <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center shadow-sm">
              <span className="text-white font-bold text-xs">FA</span>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center shadow-sm">
                <span className="text-white font-bold text-xs">FA</span>
              </div>
              <span className="text-base font-bold text-gray-800">FastAPI Admin</span>
            </div>
          )}
        </div>

        <div style={{ height: 'calc(100% - 56px)' }}>
          {menuLoading ? (
            <div className="h-full flex items-center justify-center">
              <Spin size="small" />
            </div>
          ) : (
            <Menu
              theme="light"
              mode="inline"
              selectedKeys={[location.pathname]}
              openKeys={collapsed ? [] : openKeys}
              items={menuItems}
              onOpenChange={setOpenKeys}
              onClick={({ key }) => {
                const menuItem = findMenuItem(menuItems, key)
                const targetPath = menuItem?.redirect || key
                addTab(targetPath, resolveTabLabel(targetPath))
              }}
              className="border-r-0"
              style={{ height: '100%', borderRight: 0 }}
            />
          )}
        </div>
      </Sider>

      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <div>
          <Header
            style={{
              padding: 10,
              background: 'transparent',
              height: '56px',
              lineHeight: '56px',
            }}
            className="flex items-center justify-between px-4"
          >
            <div className="flex items-center">
              <Button
                type="text"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed((previous) => !previous)}
                className="text-lg w-15 h-15 flex items-center justify-center"
              />

              <Breadcrumb items={breadcrumbItems} className="ml-3" />
            </div>

            <Dropdown
              menu={{ items: userMenuItems }}
              placement="bottomRight"
              arrow
              trigger={['click']}
              onOpenChange={(open) => {
                if (open) {
                  setUserInfo(getStoredUserInfo())
                }
              }}
            >
              <div className="cursor-pointer group">
                <Space className="px-3 py-2 rounded-lg transition-all duration-200 hover:bg-gradient-to-r hover:from-blue-50 hover:to-purple-50 hover:shadow-sm group-active:scale-95">
                  <div className="relative">
                    <Avatar
                      size={32}
                      icon={<UserOutlined />}
                      className="bg-gradient-to-br from-blue-500 to-purple-600 transition-all duration-200 group-hover:shadow-md group-hover:scale-105"
                      style={{
                        border: '2px solid transparent',
                        backgroundClip: 'padding-box',
                      }}
                    />
                    <div className="absolute -bottom-0.5 inset-y-9 -right-0.5 w-3 h-3 bg-green-500 border-2 border-white rounded-full"></div>
                  </div>
                  <div className="flex flex-col items-start">
                    <span className="text-gray-800 font-medium text-sm leading-tight group-hover:text-gray-900 transition-colors">
                      {userInfo?.nickname || userInfo?.username || '用户'}
                    </span>
                    <span className="text-gray-500 text-xs leading-tight">
                      {userInfo?.is_superuser ? '超级管理员' : '普通用户'}
                    </span>
                  </div>
                  <div className="ml-1 text-gray-400 group-hover:text-gray-600 transition-colors">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                      <path d="M6 8.5L2.5 5H9.5L6 8.5Z" />
                    </svg>
                  </div>
                </Space>
              </div>
            </Dropdown>
          </Header>

          <div className="px-2">
            <Tabs
              type="editable-card"
              activeKey={activeTab}
              onChange={handleTabChange}
              onEdit={(targetKey, action) => {
                if (action === 'remove') {
                  removeTab(targetKey)
                }
              }}
              hideAdd
              size="middle"
              className="!mb-0"
              tabBarStyle={{
                marginBottom: 0,
                borderBottom: 'none',
              }}
              items={tabs.map((tab) => ({
                key: tab.key,
                label: tab.label,
                closable: tab.closable,
              }))}
            />
          </div>
        </div>

        <Content className="p-2">
          <div
            style={{
              padding: '16px 16px',
              minHeight: 'calc(100vh - 120px)',
              background: colorBgContainer,
              borderRadius: borderRadiusLG,
            }}
            className="shadow-sm border border-gray-100"
          >
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout
