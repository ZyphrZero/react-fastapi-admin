import { AlertTriangleIcon, ArrowLeftIcon, HomeIcon, RefreshCcwIcon, ShieldAlertIcon, ServerCrashIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const errorConfig = {
  403: {
    title: '403',
    subTitle: '抱歉，您没有权限访问此页面',
    icon: ShieldAlertIcon,
  },
  404: {
    title: '404',
    subTitle: '抱歉，您访问的页面不存在',
    icon: AlertTriangleIcon,
  },
  500: {
    title: '500',
    subTitle: '抱歉，服务器出现了问题',
    icon: ServerCrashIcon,
  },
  warning: {
    title: '警告',
    subTitle: '您的操作可能存在风险',
    icon: AlertTriangleIcon,
  },
  info: {
    title: '提示',
    subTitle: '请注意相关信息',
    icon: AlertTriangleIcon,
  },
}

const ErrorPage = ({ type = '404', title, subTitle, showReload = false }) => {
  const navigate = useNavigate()
  const config = errorConfig[type] || errorConfig[404]
  const Icon = config.icon

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-lg">
        <CardHeader className="items-center text-center">
          <div className="flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <Icon />
          </div>
          <CardTitle className="text-4xl tracking-tight">{title || config.title}</CardTitle>
          <CardDescription>{subTitle || config.subTitle}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center justify-center gap-2">
          <Button onClick={() => navigate('/dashboard')}>
            <HomeIcon data-icon="inline-start" />
            返回首页
          </Button>
          <Button variant="outline" onClick={() => navigate(-1)}>
            <ArrowLeftIcon data-icon="inline-start" />
            返回上页
          </Button>
          {showReload ? (
            <Button variant="outline" onClick={() => window.location.reload()}>
              <RefreshCcwIcon data-icon="inline-start" />
              重新加载
            </Button>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}

export const NotFoundPage = () => <ErrorPage type="404" />
export const ForbiddenPage = () => <ErrorPage type="403" />
export const ServerErrorPage = () => <ErrorPage type="500" showReload />

export default ErrorPage
