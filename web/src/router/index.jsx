import { Suspense, lazy } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'

import LoginRedirect from '@/components/LoginRedirect'
import ProtectedRoute from '@/components/ProtectedRoute'

const Layout = lazy(() => import('@/components/Layout'))
const Login = lazy(() => import('@/pages/Login'))
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const Profile = lazy(() => import('@/pages/Profile'))
const UserManagement = lazy(() => import('@/pages/UserManagement'))
const RoleManagement = lazy(() => import('@/pages/RoleManagement'))
const ApiManagement = lazy(() => import('@/pages/ApiManagement'))
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
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: withSuspense(<Dashboard />),
      },
      {
        path: 'profile',
        element: withSuspense(<Profile />),
      },
      {
        path: 'system/users',
        element: withSuspense(<UserManagement />),
      },
      {
        path: 'system/roles',
        element: withSuspense(<RoleManagement />),
      },
      {
        path: 'system/apis',
        element: withSuspense(<ApiManagement />),
      },
      {
        path: 'system/departments',
        element: <div>部门管理页面</div>,
      },
      {
        path: 'system/audit',
        element: <div>审计日志页面</div>,
      },
      {
        path: 'system/upload',
        element: <div>文件管理页面</div>,
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
