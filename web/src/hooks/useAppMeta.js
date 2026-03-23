import { useEffect, useState } from 'react'

import api from '@/api'
import { APP_META_UPDATED_EVENT, defaultAppMeta } from '@/utils/appMeta'

export const useAppMeta = () => {
  const [appMeta, setAppMeta] = useState(defaultAppMeta)

  useEffect(() => {
    let active = true

    const handleMetaUpdated = (event) => {
      setAppMeta((current) => ({
        ...current,
        ...(event.detail || {}),
      }))
    }

    window.addEventListener(APP_META_UPDATED_EVENT, handleMetaUpdated)

    api.auth.getAppMeta()
      .then((response) => {
        if (!active) {
          return
        }

        setAppMeta((current) => ({
          ...current,
          ...(response.data || {}),
        }))
      })
      .catch(() => undefined)

    return () => {
      active = false
      window.removeEventListener(APP_META_UPDATED_EVENT, handleMetaUpdated)
    }
  }, [])

  return appMeta
}
