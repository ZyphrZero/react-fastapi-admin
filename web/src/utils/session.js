const ACCESS_TOKEN_KEY = 'accessToken'
const REFRESH_TOKEN_KEY = 'refreshToken'
const USER_INFO_KEY = 'userInfo'
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

export const getRefreshToken = () => storage.getItem(REFRESH_TOKEN_KEY)

export const setRefreshToken = (token) => {
  if (token) {
    storage.setItem(REFRESH_TOKEN_KEY, token)
  } else {
    storage.removeItem(REFRESH_TOKEN_KEY)
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

export const hasSession = () => Boolean(getAccessToken() || getRefreshToken())

export const clearSession = () => {
  storage.removeItem(ACCESS_TOKEN_KEY)
  storage.removeItem(REFRESH_TOKEN_KEY)
  storage.removeItem(USER_INFO_KEY)
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
