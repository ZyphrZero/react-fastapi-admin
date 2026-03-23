const ACCESS_TOKEN_KEY = 'accessToken'
const REFRESH_SESSION_KEY = 'refreshSession'
const USER_INFO_KEY = 'userInfo'
const USER_MENUS_KEY = 'userMenus'
const USER_API_PERMISSIONS_KEY = 'userApiPermissions'
const SESSION_UPDATED_EVENT = 'app:session-updated'
const storage = window.sessionStorage

const emitSessionUpdated = () => {
  window.dispatchEvent(new Event(SESSION_UPDATED_EVENT))
}

export const getAccessToken = () => storage.getItem(ACCESS_TOKEN_KEY)

export const setAccessToken = (token) => {
  if (token) {
    storage.setItem(ACCESS_TOKEN_KEY, token)
  } else {
    storage.removeItem(ACCESS_TOKEN_KEY)
  }
  emitSessionUpdated()
}

export const hasRefreshSession = () => storage.getItem(REFRESH_SESSION_KEY) === '1'

export const markRefreshSession = (enabled) => {
  if (enabled) {
    storage.setItem(REFRESH_SESSION_KEY, '1')
  } else {
    storage.removeItem(REFRESH_SESSION_KEY)
  }
  emitSessionUpdated()
}

export const getStoredUserInfo = () => {
  const raw = storage.getItem(USER_INFO_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw)
  } catch {
    storage.removeItem(USER_INFO_KEY)
    return null
  }
}

export const setStoredUserInfo = (userInfo) => {
  if (userInfo) {
    storage.setItem(USER_INFO_KEY, JSON.stringify(userInfo))
  } else {
    storage.removeItem(USER_INFO_KEY)
  }
  emitSessionUpdated()
}

export const getStoredMenus = () => {
  const raw = storage.getItem(USER_MENUS_KEY)
  if (!raw) {
    return []
  }

  try {
    return JSON.parse(raw)
  } catch {
    storage.removeItem(USER_MENUS_KEY)
    return []
  }
}

export const setStoredMenus = (menus) => {
  if (Array.isArray(menus) && menus.length > 0) {
    storage.setItem(USER_MENUS_KEY, JSON.stringify(menus))
  } else {
    storage.removeItem(USER_MENUS_KEY)
  }
  emitSessionUpdated()
}

export const getStoredApiPermissions = () => {
  const raw = storage.getItem(USER_API_PERMISSIONS_KEY)
  if (!raw) {
    return []
  }

  try {
    return JSON.parse(raw)
  } catch {
    storage.removeItem(USER_API_PERMISSIONS_KEY)
    return []
  }
}

export const setStoredApiPermissions = (permissions) => {
  if (Array.isArray(permissions) && permissions.length > 0) {
    storage.setItem(USER_API_PERMISSIONS_KEY, JSON.stringify(permissions))
  } else {
    storage.removeItem(USER_API_PERMISSIONS_KEY)
  }
  emitSessionUpdated()
}

export const hasSession = () => Boolean(getAccessToken() || hasRefreshSession())

export const clearSession = () => {
  storage.removeItem(ACCESS_TOKEN_KEY)
  storage.removeItem(REFRESH_SESSION_KEY)
  storage.removeItem(USER_INFO_KEY)
  storage.removeItem(USER_MENUS_KEY)
  storage.removeItem(USER_API_PERMISSIONS_KEY)
  emitSessionUpdated()
}

export const subscribeSessionChange = (listener) => {
  window.addEventListener(SESSION_UPDATED_EVENT, listener)
  window.addEventListener('storage', listener)

  return () => {
    window.removeEventListener(SESSION_UPDATED_EVENT, listener)
    window.removeEventListener('storage', listener)
  }
}
