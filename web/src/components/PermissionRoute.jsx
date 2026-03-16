import { Navigate, useLocation } from 'react-router-dom'

import { getStoredMenus, getStoredUserInfo, hasSession } from '@/utils/session'
import { canAccessPath } from '@/utils/permission'

const PermissionRoute = ({ children, requiredPath }) => {
  const location = useLocation()

  if (!hasSession()) {
    return <Navigate to="/login" replace />
  }

  const userInfo = getStoredUserInfo()
  if (userInfo?.is_superuser) {
    return children
  }

  const storedMenus = getStoredMenus()
  if (!canAccessPath(requiredPath, storedMenus)) {
    return <Navigate to="/forbidden" replace state={{ from: location.pathname }} />
  }

  return children
}

export default PermissionRoute
