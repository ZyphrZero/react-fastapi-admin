import { Navigate } from 'react-router-dom'
import { hasSession } from '@/utils/session'

const ProtectedRoute = ({ children }) => {
  const authenticated = hasSession()
  
  if (!authenticated) {
    return <Navigate to="/login" replace />
  }
  
  return children
}

export default ProtectedRoute 
