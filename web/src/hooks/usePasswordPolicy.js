import { useEffect, useState } from 'react'

import api from '@/api'
import { DEFAULT_PASSWORD_POLICY } from '@/utils/passwordStrength'

export const usePasswordPolicy = () => {
  const [passwordPolicy, setPasswordPolicy] = useState(DEFAULT_PASSWORD_POLICY)

  useEffect(() => {
    let active = true

    api.auth.getPasswordPolicy()
      .then((response) => {
        if (!active) {
          return
        }

        setPasswordPolicy((current) => ({
          ...current,
          ...(response.data || {}),
        }))
      })
      .catch(() => undefined)

    return () => {
      active = false
    }
  }, [])

  return passwordPolicy
}
