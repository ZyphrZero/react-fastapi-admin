const ABSOLUTE_URL_PATTERN = /^(?:https?:)?\/\//i

const getBackendOrigin = () => {
  if (typeof window === 'undefined') {
    return ''
  }

  const { protocol, hostname, origin, port } = window.location
  if (port === '5173' || port === '4173') {
    return `${protocol}//${hostname}:9999`
  }

  return origin
}

export const resolveAvatarUrl = (avatar) => {
  if (!avatar) {
    return ''
  }

  if (ABSOLUTE_URL_PATTERN.test(avatar) || avatar.startsWith('data:')) {
    return avatar
  }

  if (avatar.startsWith('/static/')) {
    return `${getBackendOrigin()}${avatar}`
  }

  return avatar
}
