import { useEffect, useMemo } from 'react'
import { Progress, Space, Typography } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { checkPasswordStrength } from '@/utils/passwordStrength'

const { Text } = Typography

/**
 * 密码强度指示器组件
 * @param {string} password - 密码值
 * @param {Function} onStrengthChange - 强度变化回调
 * @param {boolean} showSuggestions - 是否显示建议
 */
const PasswordStrengthIndicator = ({ password, onStrengthChange, showSuggestions = true }) => {
  const strength = useMemo(() => checkPasswordStrength(password || ''), [password])

  useEffect(() => {
    if (onStrengthChange) {
      onStrengthChange(strength)
    }
  }, [onStrengthChange, strength])

  const getProgressStatus = () => {
    switch (strength.level) {
      case 'strong':
        return 'success'
      case 'medium':
        return 'normal'
      case 'weak':
        return 'exception'
      default:
        return 'normal'
    }
  }

  const getStrengthIcon = () => {
    if (strength.passedAll === true) {
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />
    }
    return <InfoCircleOutlined style={{ color: strength.color }} />
  }

  const getStrengthInfo = () => {
    if (!password) {
      return {
        text: '请输入密码',
        icon: <InfoCircleOutlined style={{ color: '#d9d9d9' }} />
      }
    }

    return {
      text: `密码强度：${strength.levelText} (${strength.score}分)`,
      icon: getStrengthIcon()
    }
  }

  const strengthInfo = getStrengthInfo()

  return (
    <div style={{ marginTop: 8 }}>
      {/* 强度进度条 */}
      <div style={{ marginBottom: 8 }}>
        <Space>
          <Progress
            percent={strength.score}
            strokeColor={strength.color}
            status={getProgressStatus()}
            size="small"
            style={{ width: 120 }}
            format={() => (
              <span style={{ color: strength.color, fontSize: 12 }}>
                {strength.levelText}
              </span>
            )}
          />
          <Space size={4}>
            {strengthInfo.icon}
            <Text type="secondary" style={{ fontSize: 12 }}>
              {strengthInfo.text}
            </Text>
          </Space>
        </Space>
      </div>

      {/* 密码要求检查列表 */}
      {showSuggestions && password && (
        <div style={{ marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            密码要求：
          </Text>
          <ul style={{ margin: '4px 0 0 0', padding: 0, listStyle: 'none' }}>
            {[
              {
                key: 'length',
                text: `长度至少8个字符`,
                passed: Array.isArray(strength.passed) && strength.passed.includes('length')
              },
              {
                key: 'uppercase',
                text: '包含大写字母',
                passed: Array.isArray(strength.passed) && strength.passed.includes('uppercase')
              },
              {
                key: 'lowercase',
                text: '包含小写字母',
                passed: Array.isArray(strength.passed) && strength.passed.includes('lowercase')
              },
              {
                key: 'digits',
                text: '包含数字',
                passed: Array.isArray(strength.passed) && strength.passed.includes('digits')
              },
              {
                key: 'special',
                text: '包含特殊字符',
                passed: Array.isArray(strength.passed) && strength.passed.includes('special')
              }
            ].map((item) => (
              <li key={item.key} style={{ fontSize: 11, marginBottom: 2, display: 'flex', alignItems: 'center' }}>
                {item.passed ? (
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 4, fontSize: 10 }} />
                ) : (
                  <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 4, fontSize: 10 }} />
                )}
                <span
                  style={{
                    color: item.passed ? '#52c41a' : '#ff4d4f',
                    textDecoration: item.passed ? 'line-through' : 'none',
                    fontSize: 11
                  }}
                >
                  {item.text}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

    </div>
  )
}

export default PasswordStrengthIndicator
