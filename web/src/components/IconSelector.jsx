import { useMemo, useRef, useState } from 'react'
import { Input, Popover, Button, Space, Empty, Card } from 'antd'
import { Icon } from '@iconify/react'
import { SearchOutlined, ClearOutlined } from '@ant-design/icons'

// 预设的常用图标
const PRESET_ICONS = [
  // 系统管理类
  'carbon:gui-management',
  'material-symbols:settings-outline',
  'carbon:settings',
  'material-symbols:admin-panel-settings-outline',
  
  // 用户相关
  'material-symbols:person-outline-rounded',
  'carbon:user-role',
  'ph:users-bold',
  'carbon:user-management',
  'material-symbols:group-outline',
  
  // 菜单导航
  'material-symbols:list-alt-outline',
  'carbon:menu',
  'material-symbols:menu-outline',
  'carbon:tree-view',
  'material-symbols:folder-outline',
  
  // API和接口
  'ant-design:api-outlined',
  'carbon:api',
  'material-symbols:code-outline',
  'carbon:connection-signal',
  
  // 部门组织
  'mingcute:department-line',
  'carbon:enterprise',
  'material-symbols:business-outline',
  'carbon:building',
  
  // 日志审计
  'ph:clipboard-text-bold',
  'carbon:document',
  'material-symbols:history-outline',
  'carbon:log',
  
  // 基础功能
  'material-symbols:home-outline',
  'material-symbols:dashboard-outline',
  'carbon:analytics',
  'material-symbols:search-outline',
  'material-symbols:add-circle-outline',
  'material-symbols:edit-outline',
  'material-symbols:delete-outline',
  'material-symbols:visibility-outline',
  
  // 文件和数据
  'material-symbols:upload-file-outline',
  'material-symbols:download-outline',
  'carbon:document-attachment',
  'material-symbols:folder-open-outline',
  
  // 状态和标识
  'material-symbols:check-circle-outline',
  'material-symbols:error-outline',
  'material-symbols:warning-outline',
  'material-symbols:info-outline',
  
  // 工具类
  'material-symbols:tools-wrench-outline',
  'carbon:tools',
  'material-symbols:build-outline',
  'carbon:maintenance'
]

const IconSelector = ({ value, onChange, placeholder = "选择图标" }) => {
  const [open, setOpen] = useState(false)
  const [searchValue, setSearchValue] = useState('')
  const inputRef = useRef()

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

  const handleSearch = (e) => {
    setSearchValue(e.target.value)
  }

  const renderIconGrid = () => {
    if (filteredIcons.length === 0) {
      return (
        <Empty 
          description="未找到匹配的图标" 
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ padding: '20px 0' }}
        />
      )
    }

    return (
      <div className="grid grid-cols-6 gap-2 max-h-64 overflow-y-auto">
        {filteredIcons.map((iconName) => (
          <Card
            key={iconName}
            size="small"
            hoverable
            className={`
              cursor-pointer text-center p-2 transition-all duration-200
              ${value === iconName ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}
              hover:border-blue-400 hover:bg-blue-50
            `}
            onClick={() => handleIconSelect(iconName)}
            styles={{ body: { padding: '8px' } }}
          >
            <div className="flex flex-col items-center space-y-1">
              <Icon 
                icon={iconName} 
                width="20" 
                height="20"
                className={value === iconName ? 'text-blue-500' : 'text-gray-600'}
              />
              <div className="text-xs text-gray-500 truncate w-full text-center">
                {iconName.split(':')[1] || iconName}
              </div>
            </div>
          </Card>
        ))}
      </div>
    )
  }

  const popoverContent = (
    <div className="w-80">
      <div className="mb-3">
        <Input
          ref={inputRef}
          prefix={<SearchOutlined />}
          placeholder="搜索图标..."
          value={searchValue}
          onChange={handleSearch}
          allowClear
          autoFocus
        />
      </div>
      {renderIconGrid()}
      <div className="flex justify-end mt-3 pt-3 border-t border-gray-200">
        <Space>
          <Button size="small" onClick={handleClear}>
            清除
          </Button>
          <Button size="small" onClick={() => setOpen(false)}>
            取消
          </Button>
        </Space>
      </div>
    </div>
  )

  return (
    <Popover
      content={popoverContent}
      title="选择图标"
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomLeft"
      overlayClassName="icon-selector-popover"
    >
      <Input
        value={value}
        placeholder={placeholder}
        readOnly
        className="cursor-pointer"
        prefix={
          value ? (
            <Icon icon={value} width="16" height="16" className="text-gray-600" />
          ) : (
            <SearchOutlined className="text-gray-400" />
          )
        }
        suffix={
          value ? (
            <Button
              type="text"
              size="small"
              icon={<ClearOutlined />}
              onClick={(e) => {
                e.stopPropagation()
                handleClear()
              }}
              className="text-gray-400 hover:text-gray-600"
            />
          ) : null
        }
      />
    </Popover>
  )
}

export default IconSelector 
