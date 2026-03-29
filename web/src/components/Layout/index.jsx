import { Fragment, useEffect, useMemo, useState } from 'react'
import { Icon } from '@iconify/react'
import {
  ChevronRightIcon,
  ChevronsUpDownIcon,
  FolderTreeIcon,
  LogOutIcon,
  RefreshCcwIcon,
  Settings2Icon,
  UserCircle2Icon,
  XIcon,
} from 'lucide-react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import api from '@/api'
import BrandLogo from '@/components/BrandLogo'
import { ModeToggle } from '@/components/mode-toggle'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { Separator } from '@/components/ui/separator'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from '@/components/ui/sidebar'
import { cn } from '@/lib/utils'
import { resolveAvatarUrl } from '@/utils/avatar'
import {
  clearSession,
  getStoredMenus,
  getStoredUserInfo,
  setStoredApiPermissions,
  setStoredMenus,
  subscribeSessionChange,
} from '@/utils/session'
import { useAppMeta } from '@/hooks/useAppMeta'

const DEFAULT_TAB = {
  key: '/dashboard',
  label: '工作台',
  closable: false,
}

const DEFAULT_BREADCRUMB_LABELS = {
  '/dashboard': '工作台',
  '/profile': '个人中心',
  '/system/settings': '系统设置',
}

const mapMenuTreeToItems = (menus = []) =>
  menus
    .filter((menu) => !menu.is_hidden)
    .sort((left, right) => (left.order || 0) - (right.order || 0))
    .map((menu) => ({
      key: menu.path,
      label: menu.name,
      redirect: menu.redirect,
      icon: menu.icon,
      children: mapMenuTreeToItems(menu.children || []),
    }))

const resolveMenuTarget = (item) => item.redirect || item.key

const buildLabelMap = (items, labelMap = {}) => {
  items.forEach((item) => {
    labelMap[item.key] = item.label

    if (item.redirect) {
      labelMap[item.redirect] = item.label
    }

    if (item.children?.length) {
      buildLabelMap(item.children, labelMap)
    }
  })

  return labelMap
}

const findItemTrail = (items, targetPath, parentTrail = []) => {
  for (const item of items) {
    if (item.key === targetPath) {
      return [...parentTrail, item]
    }

    if (item.children?.length) {
      const childTrail = findItemTrail(item.children, targetPath, [...parentTrail, item])
      if (childTrail.length > 0) {
        return childTrail
      }

      if (item.redirect === targetPath) {
        return [...parentTrail, item]
      }
    }

    if (item.redirect === targetPath) {
      return [...parentTrail, item]
    }
  }

  return []
}

const buildBreadcrumbItems = (menuItems, targetPath) => {
  const matchedTrail = findItemTrail(menuItems, targetPath)

  if (matchedTrail.length > 0) {
    return matchedTrail.map((item) => ({
      key: item.key,
      label: item.label,
      path: resolveMenuTarget(item),
    }))
  }

  if (DEFAULT_BREADCRUMB_LABELS[targetPath]) {
    return [
      {
        key: targetPath,
        label: DEFAULT_BREADCRUMB_LABELS[targetPath],
        path: targetPath,
      },
    ]
  }

  return [
    {
      key: targetPath,
      label: targetPath,
      path: targetPath,
    },
  ]
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

      if (item.redirect === targetKey) {
        return [...parentKeys, item.key]
      }
    }

    if (item.redirect === targetKey) {
      return parentKeys
    }
  }

  return []
}

const hasActiveChild = (item, targetPath) => {
  if (item.key === targetPath || item.redirect === targetPath) {
    return true
  }

  return item.children?.some((child) => hasActiveChild(child, targetPath)) || false
}

const getUserInitials = (userInfo) => {
  const source = userInfo?.nickname || userInfo?.username || '用户'
  return source.replace(/\s+/g, '').slice(0, 2).toUpperCase()
}

const renderMenuIcon = (iconName) => {
  if (!iconName) {
    return <span className="size-1.5 rounded-full bg-sidebar-foreground/50" />
  }

  return <Icon icon={iconName} />
}

const UserMenu = ({ userInfo, onNavigate, onLogout }) => {
  const { isMobile } = useSidebar()

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <Avatar className="size-8 rounded-lg">
                <AvatarImage src={resolveAvatarUrl(userInfo?.avatar)} alt={userInfo?.nickname || userInfo?.username || '当前用户'} className="rounded-lg" />
                <AvatarFallback className="rounded-lg">{getUserInitials(userInfo)}</AvatarFallback>
              </Avatar>
              <div className="grid flex-1 min-w-0 text-left text-sm leading-tight">
                <span className="truncate font-medium">{userInfo?.nickname || userInfo?.username || '当前用户'}</span>
                <span className="truncate text-xs text-sidebar-foreground/70">
                  {userInfo?.email || (userInfo?.is_superuser ? '超级管理员' : '普通用户')}
                </span>
              </div>
              <ChevronsUpDownIcon className="ml-auto" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="min-w-56 rounded-lg"
            side={isMobile ? 'bottom' : 'right'}
            align="end"
            sideOffset={8}
          >
            <DropdownMenuLabel className="p-1.5">
              <div className="flex items-center gap-2 rounded-md px-1 py-1 text-left text-sm">
                <Avatar className="size-8 rounded-lg">
                  <AvatarImage src={resolveAvatarUrl(userInfo?.avatar)} alt={userInfo?.nickname || userInfo?.username || '当前用户'} className="rounded-lg" />
                  <AvatarFallback className="rounded-lg">{getUserInitials(userInfo)}</AvatarFallback>
                </Avatar>
                <div className="grid flex-1 min-w-0 text-left text-sm leading-tight">
                  <span className="truncate font-medium">{userInfo?.nickname || userInfo?.username || '当前用户'}</span>
                  <span className="truncate text-xs text-muted-foreground">
                    {userInfo?.email || (userInfo?.is_superuser ? '超级管理员' : '普通用户')}
                  </span>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem onSelect={() => onNavigate('/profile', '个人中心')}>
                <UserCircle2Icon />
                个人中心
              </DropdownMenuItem>
              {userInfo?.is_superuser ? (
                <DropdownMenuItem onSelect={() => onNavigate('/system/settings', '系统设置')}>
                  <Settings2Icon />
                  系统设置
                </DropdownMenuItem>
              ) : null}
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onSelect={() => void onLogout()}>
              <LogOutIcon />
              退出登录
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}

const AppLayout = () => {
  const [userInfo, setUserInfo] = useState(() => getStoredUserInfo())
  const [menuItems, setMenuItems] = useState(() => mapMenuTreeToItems(getStoredMenus()))
  const [menuLoading, setMenuLoading] = useState(false)
  const [openKeys, setOpenKeys] = useState([])
  const [tabs, setTabs] = useState([DEFAULT_TAB])
  const [activeTab, setActiveTab] = useState('/dashboard')
  const appMeta = useAppMeta()
  const navigate = useNavigate()
  const location = useLocation()

  const breadcrumbNameMap = useMemo(
    () => ({
      ...DEFAULT_BREADCRUMB_LABELS,
      ...buildLabelMap(menuItems),
    }),
    [menuItems],
  )

  const breadcrumbItems = useMemo(
    () => buildBreadcrumbItems(menuItems, location.pathname),
    [location.pathname, menuItems],
  )

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

  const handleGlobalRefresh = () => {
    window.location.reload()
  }

  const handleLogout = async () => {
    try {
      await api.auth.logout()
    } catch (error) {
      console.error('Logout failed:', error)
    } finally {
      clearSession()
      setUserInfo(null)
      setTabs([DEFAULT_TAB])
      setActiveTab('/dashboard')
      navigate('/login')
    }
  }

  useEffect(() => {
    let cancelled = false

    const loadMenus = async () => {
      setMenuLoading(true)

      try {
        const [menuResponse, apiPermissionResponse] = await Promise.all([
          api.auth.getUserMenu(),
          api.auth.getUserApi(),
        ])

        if (!cancelled) {
          const nextMenus = menuResponse.data || []
          setMenuItems(mapMenuTreeToItems(nextMenus))
          setStoredMenus(nextMenus)
          setStoredApiPermissions(apiPermissionResponse.data || [])
        }
      } catch (error) {
        console.error('Failed to fetch menu data:', error)

        if (!cancelled) {
          setMenuItems([])
          setStoredMenus([])
          setStoredApiPermissions([])
        }
      } finally {
        if (!cancelled) {
          setMenuLoading(false)
        }
      }
    }

    void loadMenus()

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
    const label = breadcrumbNameMap[currentPath] || currentPath

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
  }, [breadcrumbNameMap, location.pathname])

  useEffect(() => {
    setOpenKeys(findOpenKeys(menuItems, location.pathname))
  }, [location.pathname, menuItems])

  useEffect(() => {
    const currentPageLabel = breadcrumbItems[breadcrumbItems.length - 1]?.label
    const appTitle = appMeta.app_title || 'React Go Admin'

    document.title = currentPageLabel && currentPageLabel !== appTitle
      ? `${currentPageLabel} - ${appTitle}`
      : appTitle
  }, [appMeta.app_title, breadcrumbItems])

  const toggleOpenKey = (key) => {
    setOpenKeys((currentOpenKeys) =>
      currentOpenKeys.includes(key)
        ? currentOpenKeys.filter((openKey) => openKey !== key)
        : [...currentOpenKeys, key],
    )
  }

  const renderPrimaryNavigation = (items) => (
    <SidebarMenu>
      {items.map((item) => {
        const targetPath = resolveMenuTarget(item)
        const isCurrentRoute = location.pathname === targetPath
        const isGroup = item.children?.length > 0
        const isGroupActive = hasActiveChild(item, location.pathname)
        const isOpen = openKeys.includes(item.key)

        return (
          <SidebarMenuItem key={item.key}>
            <SidebarMenuButton
              tooltip={item.label}
              isActive={isCurrentRoute || isGroupActive}
              onClick={() => {
                if (isGroup) {
                  toggleOpenKey(item.key)
                  return
                }

                addTab(targetPath, resolveTabLabel(targetPath))
              }}
            >
              {renderMenuIcon(item.icon)}
              <span>{item.label}</span>
            </SidebarMenuButton>
            {isGroup ? (
              <>
                <SidebarMenuAction
                  aria-label={`展开 ${item.label}`}
                  onClick={(event) => {
                    event.preventDefault()
                    event.stopPropagation()
                    toggleOpenKey(item.key)
                  }}
                  className={cn('transition-transform', isOpen && 'rotate-90')}
                >
                  <ChevronRightIcon />
                </SidebarMenuAction>
                {isOpen ? (
                  <SidebarMenuSub>
                    {item.children.map((child) => {
                      const childTargetPath = resolveMenuTarget(child)
                      const childActive = location.pathname === childTargetPath || hasActiveChild(child, location.pathname)

                      return (
                        <SidebarMenuSubItem key={child.key}>
                          <SidebarMenuSubButton asChild isActive={childActive}>
                            <button
                              type="button"
                              onClick={() => addTab(childTargetPath, resolveTabLabel(childTargetPath))}
                            >
                              <span>{child.label}</span>
                            </button>
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      )
                    })}
                  </SidebarMenuSub>
                ) : null}
              </>
            ) : null}
          </SidebarMenuItem>
        )
      })}
    </SidebarMenu>
  )

  return (
    <SidebarProvider
      style={{
        '--sidebar-width': '18.5rem',
        '--sidebar-width-mobile': '18rem',
      }}
    >
      <Sidebar variant="inset">
        <SidebarHeader>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" asChild>
                <Link to="/dashboard">
                  <BrandLogo
                    className="min-w-0 gap-3.5"
                    markClassName="!size-10"
                    titleClassName="text-[15px]"
                    subtitleClassName="text-[10px] tracking-[0.24em]"
                    title={appMeta.app_title || 'React Go Admin'}
                    subtitle={appMeta.project_name && appMeta.project_name !== appMeta.app_title ? appMeta.project_name : 'CONTROL CENTER'}
                  />
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>主导航</SidebarGroupLabel>
            <SidebarGroupContent>
              {menuLoading ? (
                <SidebarMenu>
                  {Array.from({ length: 6 }).map((_, index) => (
                    <SidebarMenuItem key={`menu-skeleton-${index}`}>
                      <SidebarMenuSkeleton showIcon />
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              ) : menuItems.length > 0 ? (
                renderPrimaryNavigation(menuItems)
              ) : (
                <Empty className="border bg-sidebar-accent/30 py-8">
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <FolderTreeIcon />
                    </EmptyMedia>
                    <EmptyTitle>暂无可用菜单</EmptyTitle>
                    <EmptyDescription>当前账户没有可展示的导航项，或者菜单仍在同步中。</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarGroup className="mt-auto group-data-[collapsible=icon]:hidden">
            <SidebarGroupLabel>快捷入口</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton size="sm" onClick={() => addTab('/profile', '个人中心')}>
                    <UserCircle2Icon />
                    <span>个人中心</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                {userInfo?.is_superuser ? (
                  <SidebarMenuItem>
                    <SidebarMenuButton size="sm" onClick={() => addTab('/system/settings', '系统设置')}>
                      <Settings2Icon />
                      <span>系统设置</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ) : null}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter>
          <UserMenu userInfo={userInfo} onNavigate={addTab} onLogout={handleLogout} />
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>

      <SidebarInset className="min-h-svh">
        <header className="sticky top-0 z-20 flex h-16 shrink-0 items-center justify-between gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 lg:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-8" />
            <Breadcrumb>
              <BreadcrumbList>
                {breadcrumbItems.map((item, index) => {
                  const isLast = index === breadcrumbItems.length - 1

                  return (
                    <Fragment key={`${item.path}-${index}`}>
                      <BreadcrumbItem>
                        {isLast ? (
                          <BreadcrumbPage>{item.label}</BreadcrumbPage>
                        ) : (
                          <BreadcrumbLink asChild>
                            <button type="button" onClick={() => addTab(item.path, item.label)}>
                              {item.label}
                            </button>
                          </BreadcrumbLink>
                        )}
                      </BreadcrumbItem>
                      {!isLast ? <BreadcrumbSeparator className="hidden md:block" /> : null}
                    </Fragment>
                  )
                })}
              </BreadcrumbList>
            </Breadcrumb>
          </div>

          <div className="flex items-center gap-2">
            <ModeToggle />
            <Button type="button" variant="ghost" size="icon-sm" onClick={handleGlobalRefresh} aria-label="刷新当前页面">
              <RefreshCcwIcon />
            </Button>
          </div>
        </header>

        <div className="sticky top-16 z-10 border-b bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <div className="flex min-h-11 items-center gap-1 overflow-x-auto px-4 lg:px-6">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.key

              return (
                <div
                  key={tab.key}
                  className={cn(
                    'flex shrink-0 items-center rounded-md transition-colors',
                    isActive
                      ? 'bg-secondary text-secondary-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )}
                >
                  <button
                    type="button"
                    onClick={() => handleTabChange(tab.key)}
                    className="truncate px-3 py-2 text-sm"
                  >
                    {tab.label}
                  </button>
                  {tab.closable ? (
                    <button
                      type="button"
                      onClick={() => removeTab(tab.key)}
                      className="mr-1 rounded-md p-1 text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
                      aria-label={`关闭 ${tab.label}`}
                    >
                      <XIcon className="size-4" />
                    </button>
                  ) : null}
                </div>
              )
            })}
          </div>
        </div>

        <div className="flex flex-1 flex-col px-4 py-5 lg:px-6 lg:py-6">
          <div
            key={location.pathname}
            className="flex flex-1 flex-col motion-safe:animate-in motion-safe:fade-in-0 motion-safe:slide-in-from-right-2 motion-safe:duration-300"
          >
            <Outlet />
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default AppLayout
