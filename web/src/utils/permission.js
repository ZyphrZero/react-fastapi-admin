export const ALWAYS_ALLOWED_PATHS = new Set(['/profile', '/forbidden'])

export const flattenMenuPaths = (menus = []) => {
  const paths = new Set()

  const visit = (items) => {
    items.forEach((item) => {
      if (item?.path) {
        paths.add(item.path)
      }
      if (Array.isArray(item?.children) && item.children.length > 0) {
        visit(item.children)
      }
    })
  }

  visit(menus)
  return paths
}

export const canAccessPath = (path, menus = []) => {
  if (ALWAYS_ALLOWED_PATHS.has(path)) {
    return true
  }

  return flattenMenuPaths(menus).has(path)
}

export const findFirstAccessiblePath = (menus = []) => {
  for (const item of menus) {
    if (Array.isArray(item?.children) && item.children.length > 0) {
      const childPath = findFirstAccessiblePath(item.children)
      if (childPath) {
        return childPath
      }
    }

    if (item?.path) {
      return item.path
    }
  }

  return '/profile'
}
