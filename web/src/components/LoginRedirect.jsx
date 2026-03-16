import { Navigate } from 'react-router-dom'
import { hasSession } from '@/utils/session'

const LoginRedirect = () => {
  const authenticated = hasSession()
  
  if (authenticated) {
    return <Navigate to="/dashboard" replace />
  }
  
  return <Navigate to="/login" replace />
}

export default LoginRedirect 
