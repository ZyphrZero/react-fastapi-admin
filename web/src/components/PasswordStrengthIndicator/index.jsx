import { useEffect, useMemo } from 'react'
import { CheckCircle2Icon, InfoIcon, XCircleIcon } from 'lucide-react'

import { Progress } from '@/components/ui/progress'
import { checkPasswordStrength, getPasswordChecks } from '@/utils/passwordStrength'

const indicatorToneMap = {
  strong: 'text-green-600',
  medium: 'text-amber-600',
  weak: 'text-red-600',
}

const PasswordStrengthIndicator = ({ password, policy, onStrengthChange, showSuggestions = true }) => {
  const strength = useMemo(() => checkPasswordStrength(password || '', policy), [password, policy])
  const passwordChecks = useMemo(() => getPasswordChecks(policy), [policy])

  useEffect(() => {
    onStrengthChange?.(strength)
  }, [onStrengthChange, strength])

  const headline = !password
    ? { icon: <InfoIcon className="size-4 text-muted-foreground" />, text: '请输入密码' }
    : {
        icon: strength.passedAll
          ? <CheckCircle2Icon className="size-4 text-green-600" />
          : <InfoIcon className={`size-4 ${indicatorToneMap[strength.level] || 'text-muted-foreground'}`} />,
        text: `密码强度：${strength.levelText} (${strength.score} 分)`,
      }

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-muted/20 p-3">
      <div className="flex items-center gap-3">
        <div className="min-w-28">
          <Progress value={strength.score} className="h-2" />
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {headline.icon}
          <span>{headline.text}</span>
        </div>
      </div>

      {showSuggestions && password ? (
        <div className="flex flex-col gap-2">
          <div className="text-xs text-muted-foreground">密码要求</div>
          <div className="grid gap-1.5 sm:grid-cols-2">
            {passwordChecks.map((item) => {
              const passed = Array.isArray(strength.passed) && strength.passed.includes(item.key)

              return (
                <div
                  key={item.key}
                  className={`flex items-center gap-2 text-xs ${passed ? 'text-green-600' : 'text-red-600'}`}
                >
                  {passed ? <CheckCircle2Icon className="size-3.5" /> : <XCircleIcon className="size-3.5" />}
                  <span className={passed ? 'line-through' : ''}>{item.text}</span>
                </div>
              )
            })}
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default PasswordStrengthIndicator
