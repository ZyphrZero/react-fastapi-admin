import { Navigate } from 'react-router-dom'

import { findFirstAccessiblePath } from '@/utils/permission'
import { getStoredMenus } from '@/utils/session'

const HomeRedirect = () => <Navigate to={findFirstAccessiblePath(getStoredMenus())} replace />

export default HomeRedirect
