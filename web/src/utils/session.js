const TOKEN_KEY = 'token'
const USER_INFO_KEY = 'userInfo'
const SESSION_UPDATED_EVENT = 'app:session-updated'

const emitSessionUpdated = () => {
  window.dispatchEvent(new Event(SESSION_UPDATED_EVENT))
}

export const getAccessToken = () => localStorage.getItem(TOKEN_KEY)

export const setAccessToken = (token) => {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
  emitSessionUpdated()
}

export const getStoredUserInfo = () => {
  const raw = localStorage.getItem(USER_INFO_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw)
  } catch {
    localStorage.removeItem(USER_INFO_KEY)
    return null
  }
}

export const setStoredUserInfo = (userInfo) => {
  if (userInfo) {
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo))
  } else {
    localStorage.removeItem(USER_INFO_KEY)
  }
  emitSessionUpdated()
}

export const clearSession = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_INFO_KEY)
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
