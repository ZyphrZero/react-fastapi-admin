import { Suspense, lazy } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'

import LoginRedirect from '@/components/LoginRedirect'
import ProtectedRoute from '@/components/ProtectedRoute'
import SuperuserRoute from '@/components/SuperuserRoute'

const Layout = lazy(() => import('@/components/Layout'))
const Login = lazy(() => import('@/pages/Login'))
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const Profile = lazy(() => import('@/pages/Profile'))
const UserManagement = lazy(() => import('@/pages/UserManagement'))
const RoleManagement = lazy(() => import('@/pages/RoleManagement'))
const ApiManagement = lazy(() => import('@/pages/ApiManagement'))
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
        element: (
          <SuperuserRoute>
            {withSuspense(<UserManagement />)}
          </SuperuserRoute>
        ),
      },
      {
        path: 'system/roles',
        element: (
          <SuperuserRoute>
            {withSuspense(<RoleManagement />)}
          </SuperuserRoute>
        ),
      },
      {
        path: 'system/apis',
        element: (
          <SuperuserRoute>
            {withSuspense(<ApiManagement />)}
          </SuperuserRoute>
        ),
      },
      {
        path: 'system/departments',
        element: (
          <SuperuserRoute>
            <div>部门管理页面</div>
          </SuperuserRoute>
        ),
      },
      {
        path: 'system/audit',
        element: (
          <SuperuserRoute>
            <div>审计日志页面</div>
          </SuperuserRoute>
        ),
      },
      {
        path: 'system/upload',
        element: (
          <SuperuserRoute>
            <div>文件管理页面</div>
          </SuperuserRoute>
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
