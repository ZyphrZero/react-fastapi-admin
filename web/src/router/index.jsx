/* eslint-disable react-refresh/only-export-components */
import { Suspense, lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'

import HomeRedirect from '@/components/HomeRedirect'
import LoginRedirect from '@/components/LoginRedirect'
import PermissionRoute from '@/components/PermissionRoute'
import ProtectedRoute from '@/components/ProtectedRoute'

const Layout = lazy(() => import('@/components/Layout'))
const Login = lazy(() => import('@/pages/Login'))
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const AuditLog = lazy(() => import('@/pages/AuditLog'))
const Profile = lazy(() => import('@/pages/Profile'))
const UserManagement = lazy(() => import('@/pages/UserManagement'))
const RoleManagement = lazy(() => import('@/pages/RoleManagement'))
const ApiManagement = lazy(() => import('@/pages/ApiManagement'))
const SystemSettings = lazy(() => import('@/pages/SystemSettings'))
const ForbiddenPage = lazy(() => import('@/pages/ErrorPages').then((module) => ({ default: module.ForbiddenPage })))
const NotFoundPage = lazy(() => import('@/pages/ErrorPages').then((module) => ({ default: module.NotFoundPage })))

const routeFallback = (
  <div className="min-h-[320px] flex items-center justify-center">
    <div className="text-center">
      <div className="w-10 h-10 mx-auto rounded-full border-2 border-slate-200 border-t-blue-600 animate-spin"></div>
      <p className="mt-4 text-sm text-slate-500">页面加载中...</p>
    </div>
  </div>
)

const withSuspense = (node) => <Suspense fallback={routeFallback}>{node}</Suspense>

const router = createBrowserRouter([
  {
    path: '/login',
    element: withSuspense(<Login />),
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        {withSuspense(<Layout />)}
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <HomeRedirect />,
      },
      {
        path: 'dashboard',
        element: (
          <PermissionRoute requiredPath="/dashboard">
            {withSuspense(<Dashboard />)}
          </PermissionRoute>
        ),
      },
      {
        path: 'profile',
        element: withSuspense(<Profile />),
      },
      {
        path: 'system/settings',
        element: (
          <PermissionRoute requiredPath="/system/settings">
            {withSuspense(<SystemSettings />)}
          </PermissionRoute>
        ),
      },
      {
        path: 'system/users',
        element: (
          <PermissionRoute requiredPath="/system/users">
            {withSuspense(<UserManagement />)}
          </PermissionRoute>
        ),
      },
      {
        path: 'system/roles',
        element: (
          <PermissionRoute requiredPath="/system/roles">
            {withSuspense(<RoleManagement />)}
          </PermissionRoute>
        ),
      },
      {
        path: 'system/apis',
        element: (
          <PermissionRoute requiredPath="/system/apis">
            {withSuspense(<ApiManagement />)}
          </PermissionRoute>
        ),
      },
      {
        path: 'system/audit',
        element: (
          <PermissionRoute requiredPath="/system/audit">
            {withSuspense(<AuditLog />)}
          </PermissionRoute>
        ),
      },
      {
        path: 'system/upload',
        element: (
          <PermissionRoute requiredPath="/system/upload">
            <div>文件管理页面</div>
          </PermissionRoute>
        ),
      },
      {
        path: 'forbidden',
        element: withSuspense(<ForbiddenPage />),
      },
      {
        path: '*',
        element: withSuspense(<NotFoundPage />),
      },
    ],
  },
  {
    path: '/auth/callback',
    element: <LoginRedirect />,
  },
])

export default router
