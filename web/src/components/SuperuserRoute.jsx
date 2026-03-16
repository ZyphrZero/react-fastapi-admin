import { Navigate, useLocation } from 'react-router-dom'

import { getStoredUserInfo, hasSession } from '@/utils/session'

const SuperuserRoute = ({ children }) => {
  const location = useLocation()

  if (!hasSession()) {
    return <Navigate to="/login" replace />
  }

  const userInfo = getStoredUserInfo()
  if (!userInfo?.is_superuser) {
    return <Navigate to="/forbidden" replace state={{ from: location.pathname }} />
  }

  return children
}

export default SuperuserRoute
