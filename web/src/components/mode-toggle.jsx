import { useRef } from 'react'
import { LaptopMinimalIcon, MoonStarIcon, SunIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import { useTheme } from '@/components/theme-provider'

const themeOptions = [
  {
    value: 'light',
    label: '浅色',
    icon: SunIcon,
  },
  {
    value: 'dark',
    label: '深色',
    icon: MoonStarIcon,
  },
  {
    value: 'system',
    label: '跟随系统',
    icon: LaptopMinimalIcon,
  },
]

const resolvedThemeLabelMap = {
  light: '浅色',
  dark: '深色',
}

export function ModeToggle({ className }) {
  const { theme, resolvedTheme, setTheme } = useTheme()
  const triggerRef = useRef(null)

  const handleThemeChange = (nextTheme) => {
    const rect = triggerRef.current?.getBoundingClientRect()

    if (!rect) {
      setTheme(nextTheme)
      return
    }

    setTheme(nextTheme, {
      origin: {
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height / 2,
      },
    })
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button ref={triggerRef} variant="outline" size="icon" className={cn('relative rounded-full', className)}>
          <SunIcon className="scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
          <MoonStarIcon className="absolute scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
          <span className="sr-only">切换界面主题</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuLabel>界面主题</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup value={theme} onValueChange={handleThemeChange}>
          {themeOptions.map((option) => {
            const OptionIcon = option.icon

            return (
              <DropdownMenuRadioItem key={option.value} value={option.value}>
                <OptionIcon />
                <span>{option.label}</span>
              </DropdownMenuRadioItem>
            )
          })}
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />
        <div className="px-2 py-1 text-xs text-muted-foreground">
          当前生效：{resolvedThemeLabelMap[resolvedTheme] || '浅色'}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
