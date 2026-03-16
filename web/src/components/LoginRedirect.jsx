import { Navigate } from 'react-router-dom'
import { getAccessToken } from '@/utils/session'

const LoginRedirect = () => {
  const token = getAccessToken()
  
  if (token) {
    return <Navigate to="/dashboard" replace />
  }
  
  return <Navigate to="/login" replace />
}

export default LoginRedirect 
