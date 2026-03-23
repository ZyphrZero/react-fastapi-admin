import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'

const THEME_VALUES = ['light', 'dark', 'system']
const THEME_TRANSITION_MAX_ELEMENTS = 2500
const THEME_TRANSITION_MAX_TABLE_ROWS = 80

const ThemeProviderContext = createContext({
  theme: 'system',
  resolvedTheme: 'light',
  setTheme: () => null,
})

const getSystemTheme = () =>
  window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'

const normalizeTheme = (value, fallback) => (THEME_VALUES.includes(value) ? value : fallback)

const disableTransitionsTemporarily = () => {
  const style = window.document.createElement('style')

  style.appendChild(
    window.document.createTextNode(
      '*,*::before,*::after{transition:none !important;animation:none !important}',
    ),
  )

  window.document.head.appendChild(style)

  return () => {
    window.getComputedStyle(window.document.body)
    window.requestAnimationFrame(() => {
      style.remove()
    })
  }
}

const applyResolvedThemeToRoot = (nextResolvedTheme) => {
  const root = window.document.documentElement

  root.classList.remove('light', 'dark')
  root.classList.add(nextResolvedTheme)
  root.style.colorScheme = nextResolvedTheme
}

const supportsThemeViewTransition = () =>
  typeof window !== 'undefined' &&
  typeof document !== 'undefined' &&
  typeof document.startViewTransition === 'function'

const shouldAnimateThemeTransition = () => {
  if (!supportsThemeViewTransition()) {
    return false
  }

  const root = window.document.getElementById('root')
  const elementCount = root?.getElementsByTagName('*').length ?? window.document.getElementsByTagName('*').length
  const tableRowCount = root?.querySelectorAll('[data-slot="table-row"]').length ?? 0

  return elementCount <= THEME_TRANSITION_MAX_ELEMENTS && tableRowCount <= THEME_TRANSITION_MAX_TABLE_ROWS
}

const getThemeTransitionRadius = (x, y) => {
  const maxHorizontalDistance = Math.max(x, window.innerWidth - x)
  const maxVerticalDistance = Math.max(y, window.innerHeight - y)

  return Math.hypot(maxHorizontalDistance, maxVerticalDistance)
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'vite-ui-theme',
}) {
  const [theme, setThemeState] = useState(() => {
    const storedTheme = window.localStorage.getItem(storageKey)
    return normalizeTheme(storedTheme, defaultTheme)
  })
  const [systemTheme, setSystemTheme] = useState(() => getSystemTheme())
  const appliedThemeRef = useRef(null)

  const resolvedTheme = theme === 'system' ? systemTheme : theme

  const applyResolvedTheme = useCallback((nextResolvedTheme, transitionOrigin = null) => {
    if (appliedThemeRef.current === nextResolvedTheme && !transitionOrigin) {
      return
    }

    const root = window.document.documentElement

    if (transitionOrigin && shouldAnimateThemeTransition()) {
      const { x, y } = transitionOrigin
      const radius = getThemeTransitionRadius(x, y)

      root.style.setProperty('--theme-transition-x', `${x}px`)
      root.style.setProperty('--theme-transition-y', `${y}px`)
      root.style.setProperty('--theme-transition-radius', `${radius}px`)

      document.startViewTransition(() => {
        applyResolvedThemeToRoot(nextResolvedTheme)
      })
    } else {
      const restoreTransitions = disableTransitionsTemporarily()
      applyResolvedThemeToRoot(nextResolvedTheme)
      restoreTransitions()
    }

    appliedThemeRef.current = nextResolvedTheme
  }, [])

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleSystemThemeChange = () => {
      setSystemTheme(getSystemTheme())
    }

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', handleSystemThemeChange)
      return () => mediaQuery.removeEventListener('change', handleSystemThemeChange)
    }

    mediaQuery.addListener(handleSystemThemeChange)
    return () => mediaQuery.removeListener(handleSystemThemeChange)
  }, [])

  useLayoutEffect(() => {
    applyResolvedTheme(resolvedTheme)
  }, [applyResolvedTheme, resolvedTheme])

  const setTheme = useCallback((nextTheme, options = {}) => {
    const normalizedTheme = normalizeTheme(nextTheme, defaultTheme)
    const nextResolvedTheme = normalizedTheme === 'system' ? getSystemTheme() : normalizedTheme

    window.localStorage.setItem(storageKey, normalizedTheme)
    applyResolvedTheme(nextResolvedTheme, options.origin ?? null)
    setThemeState(normalizedTheme)
  }, [applyResolvedTheme, defaultTheme, storageKey])

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
    }),
    [resolvedTheme, setTheme, theme],
  )

  return <ThemeProviderContext.Provider value={value}>{children}</ThemeProviderContext.Provider>
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext)

  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }

  return context
}
