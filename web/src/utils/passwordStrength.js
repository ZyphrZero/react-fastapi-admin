export const DEFAULT_PASSWORD_POLICY = {
  password_min_length: 8,
  password_require_uppercase: true,
  password_require_lowercase: true,
  password_require_digits: true,
  password_require_special: true,
}

export const normalizePasswordPolicy = (policy = {}) => ({
  ...DEFAULT_PASSWORD_POLICY,
  ...policy,
})

export const getPasswordChecks = (policy = {}) => {
  const normalizedPolicy = normalizePasswordPolicy(policy)
  const checks = [{ key: 'length', text: `长度至少 ${normalizedPolicy.password_min_length} 个字符` }]

  if (normalizedPolicy.password_require_uppercase) checks.push({ key: 'uppercase', text: '包含大写字母' })
  if (normalizedPolicy.password_require_lowercase) checks.push({ key: 'lowercase', text: '包含小写字母' })
  if (normalizedPolicy.password_require_digits) checks.push({ key: 'digits', text: '包含数字' })
  if (normalizedPolicy.password_require_special) checks.push({ key: 'special', text: '包含特殊字符' })

  return checks
}

export const validatePasswordAgainstPolicy = (password, policy = {}) => {
  const normalizedPolicy = normalizePasswordPolicy(policy)

  if (!password) return '请输入密码'
  if (password.length < normalizedPolicy.password_min_length) {
    return `密码长度不能少于 ${normalizedPolicy.password_min_length} 个字符`
  }
  if (normalizedPolicy.password_require_uppercase && !/[A-Z]/.test(password)) return '密码必须包含至少一个大写字母'
  if (normalizedPolicy.password_require_lowercase && !/[a-z]/.test(password)) return '密码必须包含至少一个小写字母'
  if (normalizedPolicy.password_require_digits && !/\d/.test(password)) return '密码必须包含至少一个数字'
  if (normalizedPolicy.password_require_special && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) return '密码必须包含至少一个特殊字符'

  return ''
}

export const checkPasswordStrength = (password, policy = {}) => {
  const normalizedPolicy = normalizePasswordPolicy(policy)
  const checks = getPasswordChecks(normalizedPolicy)

  if (!password) {
    return {
      score: 0,
      level: 'weak',
      levelText: '弱',
      color: '#ff4d4f',
      suggestions: ['请输入密码'],
      passed: [],
      passedAll: false,
    }
  }

  let score = 0
  const suggestions = []
  const passed = []
  const pointsPerCheck = 100 / checks.length

  if (password.length >= normalizedPolicy.password_min_length) {
    score += pointsPerCheck
    passed.push('length')
  } else {
    suggestions.push(`密码长度至少 ${normalizedPolicy.password_min_length} 个字符`)
  }

  if (normalizedPolicy.password_require_uppercase) {
    if (/[A-Z]/.test(password)) {
      score += pointsPerCheck
      passed.push('uppercase')
    } else {
      suggestions.push('包含至少一个大写字母')
    }
  }

  if (normalizedPolicy.password_require_lowercase) {
    if (/[a-z]/.test(password)) {
      score += pointsPerCheck
      passed.push('lowercase')
    } else {
      suggestions.push('包含至少一个小写字母')
    }
  }

  if (normalizedPolicy.password_require_digits) {
    if (/\d/.test(password)) {
      score += pointsPerCheck
      passed.push('digits')
    } else {
      suggestions.push('包含至少一个数字')
    }
  }

  if (normalizedPolicy.password_require_special) {
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      score += pointsPerCheck
      passed.push('special')
    } else {
      suggestions.push('包含至少一个特殊字符 (!@#$%^&*(),.?":{}|<>)')
    }
  }

  const finalScore = Math.min(100, Math.round(score))
  const passedAll = passed.length === checks.length
  const level = passedAll ? 'strong' : passed.length >= Math.ceil(checks.length * 0.7) ? 'medium' : 'weak'
  const levelText = level === 'strong' ? '强' : level === 'medium' ? '中' : '弱'
  const color = level === 'strong' ? '#52c41a' : level === 'medium' ? '#faad14' : '#ff4d4f'

  return {
    score: finalScore,
    level,
    levelText,
    color,
    suggestions,
    passed,
    passedAll,
  }
}
