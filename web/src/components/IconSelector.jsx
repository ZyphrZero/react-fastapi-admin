import { useMemo, useState } from 'react'
import { Icon } from '@iconify/react'
import { SearchIcon, XIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'

const PRESET_ICONS = [
  'carbon:gui-management',
  'material-symbols:settings-outline',
  'carbon:settings',
  'material-symbols:admin-panel-settings-outline',
  'material-symbols:person-outline-rounded',
  'carbon:user-role',
  'ph:users-bold',
  'carbon:user-management',
  'material-symbols:group-outline',
  'material-symbols:list-alt-outline',
  'carbon:menu',
  'material-symbols:menu-outline',
  'carbon:tree-view',
  'material-symbols:folder-outline',
  'ant-design:api-outlined',
  'carbon:api',
  'material-symbols:code-outline',
  'carbon:connection-signal',
  'carbon:enterprise',
  'material-symbols:business-outline',
  'carbon:building',
  'ph:clipboard-text-bold',
  'carbon:document',
  'material-symbols:history-outline',
  'carbon:log',
  'material-symbols:home-outline',
  'material-symbols:dashboard-outline',
  'carbon:analytics',
  'material-symbols:search-outline',
  'material-symbols:add-circle-outline',
  'material-symbols:edit-outline',
  'material-symbols:delete-outline',
  'material-symbols:visibility-outline',
  'material-symbols:upload-file-outline',
  'material-symbols:download-outline',
  'carbon:document-attachment',
  'material-symbols:folder-open-outline',
  'material-symbols:check-circle-outline',
  'material-symbols:error-outline',
  'material-symbols:warning-outline',
  'material-symbols:info-outline',
  'material-symbols:tools-wrench-outline',
  'carbon:tools',
  'material-symbols:build-outline',
  'carbon:maintenance',
]

const IconSelector = ({ value, onChange, placeholder = '选择图标' }) => {
  const [open, setOpen] = useState(false)
  const [searchValue, setSearchValue] = useState('')

  const filteredIcons = useMemo(() => {
    if (!searchValue.trim()) {
      return PRESET_ICONS
    }

    return PRESET_ICONS.filter((icon) => icon.toLowerCase().includes(searchValue.toLowerCase()))
  }, [searchValue])

  const handleIconSelect = (iconName) => {
    onChange?.(iconName)
    setOpen(false)
    setSearchValue('')
  }

  const handleClear = () => {
    onChange?.('')
    setOpen(false)
  }

  return (
    <>
      <button
        type="button"
        className="flex h-8 w-full items-center justify-between rounded-lg border border-input bg-transparent px-2.5 text-left text-sm text-foreground transition-colors hover:bg-muted/50"
        onClick={() => setOpen(true)}
      >
        <span className="flex min-w-0 items-center gap-2">
          {value ? <Icon icon={value} width="16" height="16" /> : <SearchIcon className="size-4 text-muted-foreground" />}
          <span className={`truncate ${value ? 'text-foreground' : 'text-muted-foreground'}`}>
            {value || placeholder}
          </span>
        </span>
        {value ? (
          <span
            className="rounded p-1 text-muted-foreground hover:bg-muted"
            onClick={(event) => {
              event.stopPropagation()
              handleClear()
            }}
          >
            <XIcon className="size-4" />
          </span>
        ) : null}
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>选择图标</DialogTitle>
            <DialogDescription>从预设图标中选择一个菜单图标</DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <Input
              value={searchValue}
              placeholder="搜索图标..."
              onChange={(event) => setSearchValue(event.target.value)}
            />

            {filteredIcons.length > 0 ? (
              <div className="grid max-h-80 grid-cols-4 gap-2 overflow-y-auto pr-1 sm:grid-cols-6">
                {filteredIcons.map((iconName) => (
                  <button
                    key={iconName}
                    type="button"
                    className={`flex flex-col items-center gap-2 rounded-lg border p-3 text-center text-xs transition-colors ${
                      value === iconName ? 'border-primary bg-muted' : 'hover:bg-muted/50'
                    }`}
                    onClick={() => handleIconSelect(iconName)}
                  >
                    <Icon icon={iconName} width="20" height="20" />
                    <span className="w-full truncate">{iconName.split(':')[1] || iconName}</span>
                  </button>
                ))}
              </div>
            ) : (
              <Empty className="border bg-muted/20 py-8">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <SearchIcon />
                  </EmptyMedia>
                  <EmptyTitle>未找到匹配的图标</EmptyTitle>
                  <EmptyDescription>换个关键词再试一次。</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClear}>
              清除
            </Button>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              取消
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export default IconSelector
