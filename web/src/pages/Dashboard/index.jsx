import { useEffect, useState } from 'react'
import {
  ActivityIcon,
  DatabaseIcon,
  RefreshCcwIcon,
  ShieldCheckIcon,
  UsersIcon,
  WaypointsIcon,
  WebhookIcon,
} from 'lucide-react'

import api from '@/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'

const statusVariantMap = {
  online: 'secondary',
  offline: 'outline',
  production: 'destructive',
  default: 'outline',
}

const statusDistributionStyleMap = {
  '2xx': {
    badgeVariant: 'secondary',
    barClassName: 'bg-emerald-500/80',
  },
  '3xx': {
    badgeVariant: 'outline',
    barClassName: 'bg-sky-500/80',
  },
  '4xx': {
    badgeVariant: 'outline',
    barClassName: 'bg-amber-500/80',
  },
  '5xx': {
    badgeVariant: 'destructive',
    barClassName: 'bg-rose-500/80',
  },
  other: {
    badgeVariant: 'outline',
    barClassName: 'bg-slate-500/80',
  },
}

const resolveHttpStatusVariant = (status) => {
  if (status >= 500) {
    return 'destructive'
  }

  if (status >= 400) {
    return 'outline'
  }

  return 'secondary'
}

const formatBooleanBadge = (value, truthyText, falsyText) => ({
  label: value ? truthyText : falsyText,
  variant: value ? 'secondary' : 'outline',
})

const formatShortDateLabel = (value) => {
  if (!value) {
    return '--'
  }

  const segments = String(value).split('-')
  if (segments.length === 3) {
    return `${segments[1]}/${segments[2]}`
  }

  return value
}

const buildTrendPoints = (items, width, height, paddingX, paddingTop, paddingBottom) => {
  if (!items.length) {
    return []
  }

  const baselineY = height - paddingBottom
  const maxCount = Math.max(...items.map((item) => item.count), 0)

  return items.map((item, index) => {
    const x = items.length === 1
      ? width / 2
      : paddingX + (index * (width - paddingX * 2)) / (items.length - 1)
    const y = maxCount > 0
      ? baselineY - (item.count / maxCount) * (baselineY - paddingTop)
      : baselineY

    return {
      ...item,
      x,
      y,
    }
  })
}

const buildSmoothSegments = (points) =>
  points.slice(1).map((point, index) => {
    const previous = points[index]
    const controlX = (previous.x + point.x) / 2

    return ` C ${controlX} ${previous.y}, ${controlX} ${point.y}, ${point.x} ${point.y}`
  }).join('')

const buildSmoothLinePath = (points) => {
  if (!points.length) {
    return ''
  }

  return `M ${points[0].x} ${points[0].y}${buildSmoothSegments(points)}`
}

const buildSmoothAreaPath = (points, baselineY) => {
  if (!points.length) {
    return ''
  }

  const segments = buildSmoothSegments(points)
  const lastPoint = points[points.length - 1]

  return `M ${points[0].x} ${baselineY} L ${points[0].x} ${points[0].y}${segments} L ${lastPoint.x} ${baselineY} Z`
}

const DashboardSkeleton = () => (
  <div className="flex flex-col gap-5">
    <div className="flex flex-col gap-4 border-b pb-5 md:flex-row md:items-end md:justify-between">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-full max-w-md" />
      </div>
      <div className="flex flex-wrap gap-2">
        <Skeleton className="h-8 w-20 rounded-lg" />
        <Skeleton className="h-8 w-24 rounded-lg" />
        <Skeleton className="h-8 w-24 rounded-lg" />
        <Skeleton className="h-8 w-28 rounded-lg" />
      </div>
    </div>

    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      {Array.from({ length: 4 }).map((_, index) => (
        <Card key={`stat-skeleton-${index}`}>
          <CardHeader className="pb-0">
            <div className="flex items-start justify-between gap-3">
              <div className="flex flex-col gap-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-20" />
              </div>
              <Skeleton className="size-9 rounded-lg" />
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <Skeleton className="h-4 w-24" />
          </CardContent>
        </Card>
      ))}
    </div>

    <div className="grid gap-4 xl:grid-cols-[0.72fr_1.28fr]">
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-0">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={`status-skeleton-${index}`} className="flex items-center justify-between gap-3 border-b pb-3 last:border-b-0 last:pb-0">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-6 w-20 rounded-full" />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-28" />
          <Skeleton className="h-4 w-36" />
        </CardHeader>
        <CardContent className="flex flex-col gap-4 pt-0">
          <div className="grid gap-2 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={`trend-meta-${index}`} className="h-16 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-64 rounded-xl" />
        </CardContent>
      </Card>
    </div>

    <div className="grid gap-4 xl:grid-cols-2">
      {Array.from({ length: 2 }).map((_, index) => (
        <Card key={`chart-skeleton-${index}`}>
          <CardHeader>
            <Skeleton className="h-5 w-28" />
            <Skeleton className="h-4 w-40" />
          </CardHeader>
          <CardContent className="flex flex-col gap-4 pt-0">
            {Array.from({ length: 4 }).map((_, rowIndex) => (
              <div key={`chart-row-${index}-${rowIndex}`} className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-3">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-12" />
                </div>
                <Skeleton className="h-2 rounded-full" />
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>

    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-col gap-1">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="size-9 rounded-lg" />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex flex-col gap-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={`table-skeleton-${index}`} className="h-10 w-full rounded-xl" />
          ))}
        </div>
      </CardContent>
    </Card>
  </div>
)

const TrendLineChart = ({ items }) => {
  if (!items.length) {
    return (
      <Empty className="border bg-muted/20 py-10">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <WaypointsIcon />
          </EmptyMedia>
          <EmptyTitle>暂无趋势数据</EmptyTitle>
          <EmptyDescription>最近 7 天还没有可展示的操作趋势。</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  const chartWidth = 100
  const chartHeight = 52
  const paddingX = 6
  const paddingTop = 6
  const paddingBottom = 10
  const baselineY = chartHeight - paddingBottom
  const points = buildTrendPoints(items, chartWidth, chartHeight, paddingX, paddingTop, paddingBottom)
  const linePath = buildSmoothLinePath(points)
  const areaPath = buildSmoothAreaPath(points, baselineY)
  const totalCount = items.reduce((sum, item) => sum + item.count, 0)
  const averageCount = items.length ? Math.round(totalCount / items.length) : 0
  const peakItem = items.reduce((currentPeak, item) => {
    if (!currentPeak || item.count > currentPeak.count) {
      return item
    }
    return currentPeak
  }, null)

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-2 sm:grid-cols-3">
        <div className="rounded-xl border bg-muted/20 p-3">
          <div className="text-xs text-muted-foreground">7 天累计</div>
          <div className="mt-1 text-2xl font-semibold">{totalCount}</div>
          <div className="text-xs text-muted-foreground">最近一周总操作量</div>
        </div>
        <div className="rounded-xl border bg-muted/20 p-3">
          <div className="text-xs text-muted-foreground">日均操作</div>
          <div className="mt-1 text-2xl font-semibold">{averageCount}</div>
          <div className="text-xs text-muted-foreground">平均每日请求次数</div>
        </div>
        <div className="rounded-xl border bg-muted/20 p-3">
          <div className="text-xs text-muted-foreground">峰值日期</div>
          <div className="mt-1 text-2xl font-semibold">{peakItem ? formatShortDateLabel(peakItem.date) : '--'}</div>
          <div className="text-xs text-muted-foreground">{peakItem ? `${peakItem.count} 次操作` : '暂无数据'}</div>
        </div>
      </div>

      <div className="rounded-xl border bg-muted/10 p-4">
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="h-56 w-full">
          <defs>
            <linearGradient id="dashboard-trend-area" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.22" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {Array.from({ length: 4 }).map((_, index) => {
            const y = paddingTop + ((baselineY - paddingTop) * index) / 3

            return (
              <line
                key={`trend-grid-${index}`}
                x1={paddingX}
                x2={chartWidth - paddingX}
                y1={y}
                y2={y}
                stroke="currentColor"
                strokeOpacity="0.08"
                strokeDasharray="1.5 2.5"
              />
            )
          })}

          {areaPath ? (
            <path
              d={areaPath}
              fill="url(#dashboard-trend-area)"
              className="text-primary"
            />
          ) : null}

          {linePath ? (
            <path
              d={linePath}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-primary"
            />
          ) : null}

          {points.map((point) => (
            <g key={point.date}>
              <circle
                cx={point.x}
                cy={point.y}
                r="2.6"
                fill="currentColor"
                className="text-primary"
              />
              <circle
                cx={point.x}
                cy={point.y}
                r="1.2"
                fill="currentColor"
                className="text-background"
              />
            </g>
          ))}
        </svg>

        <div className="mt-4 grid grid-cols-7 gap-2">
          {items.map((item) => (
            <div key={item.date} className="min-w-0 rounded-lg bg-background/60 px-2 py-2 text-center">
              <div className="truncate text-[11px] text-muted-foreground">{formatShortDateLabel(item.date)}</div>
              <div className="text-sm font-medium">{item.count}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const DistributionChart = ({
  items,
  emptyIcon: EmptyIcon,
  emptyTitle,
  emptyDescription,
  renderLeading,
  countSuffix = '次',
}) => {
  if (!items.length) {
    return (
      <Empty className="border bg-muted/20 py-10">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <EmptyIcon />
          </EmptyMedia>
          <EmptyTitle>{emptyTitle}</EmptyTitle>
          <EmptyDescription>{emptyDescription}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  const maxCount = Math.max(...items.map((item) => item.count), 0)

  return (
    <div className="flex flex-col gap-4">
      {items.map((item) => {
        const width = maxCount > 0 ? Math.max(Math.round((item.count / maxCount) * 100), 8) : 0

        return (
          <div key={item.key || item.label} className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                {renderLeading ? renderLeading(item) : null}
                <span className="truncate text-sm font-medium">{item.label}</span>
              </div>
              <div className="shrink-0 text-sm text-muted-foreground">{item.count} {countSuffix}</div>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className={cn('h-full rounded-full bg-primary/80 transition-[width]', item.barClassName)}
                style={{ width: `${width}%` }}
              />
            </div>
            <div className="text-xs text-muted-foreground">占比 {item.share}%</div>
          </div>
        )
      })}
    </div>
  )
}

const Dashboard = () => {
  const [loading, setLoading] = useState(false)
  const [overview, setOverview] = useState(null)
  const [refreshTick, setRefreshTick] = useState(0)

  useEffect(() => {
    let cancelled = false

    const loadOverview = async () => {
      setLoading(true)

      try {
        const response = await api.auth.getOverview()

        if (!cancelled) {
          setOverview(response.data || null)
        }
      } catch (error) {
        console.error('获取概览数据失败:', error)

        if (!cancelled) {
          setOverview(null)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadOverview()

    return () => {
      cancelled = true
    }
  }, [refreshTick])

  const summary = overview?.summary || {}
  const system = overview?.system || {}
  const charts = overview?.charts || {}
  const auditTrend = overview?.audit_trend || []
  const recentActivities = overview?.recent_activities || []
  const moduleActivity = charts.module_activity || []
  const statusDistribution = (charts.status_distribution || []).map((item) => ({
    ...item,
    badgeVariant: statusDistributionStyleMap[item.key]?.badgeVariant || 'outline',
    barClassName: statusDistributionStyleMap[item.key]?.barClassName || 'bg-primary/80',
  }))
  const environment = system.environment || 'unknown'
  const environmentVariant = String(environment).toLowerCase() === 'production' ? 'destructive' : 'secondary'
  const runMigrationsOnStartup = system.run_migrations_on_startup ?? system.auto_migration ?? false
  const seedBaseDataOnStartup = system.seed_base_data_on_startup ?? system.auto_seed_data ?? false
  const refreshApiMetadataOnStartup = system.refresh_api_metadata_on_startup ?? system.auto_refresh_api ?? false
  const chartActivityTotal = moduleActivity.reduce((sum, item) => sum + item.count, 0)

  const statistics = [
    {
      key: 'users',
      title: '用户总数',
      value: summary.user_total || 0,
      extra: `启用 ${summary.active_user_total || 0}`,
      icon: UsersIcon,
    },
    {
      key: 'roles',
      title: '角色数量',
      value: summary.role_total || 0,
      extra: '权限角色池',
      icon: ShieldCheckIcon,
    },
    {
      key: 'apis',
      title: 'API 数量',
      value: summary.api_total || 0,
      extra: '接口元数据',
      icon: WebhookIcon,
    },
    {
      key: 'audits',
      title: '今日操作',
      value: summary.today_audit_total || 0,
      extra: '审计记录',
      icon: ActivityIcon,
    },
  ]

  const systemStatusItems = [
    {
      label: '运行环境',
      value: environment,
      variant: environmentVariant,
    },
    {
      label: '数据库',
      value: system.database || 'sqlite',
      variant: statusVariantMap.default,
    },
    {
      label: '访问日志',
      ...formatBooleanBadge(system.access_log_enabled, '已启用', '已关闭'),
    },
    {
      label: '自动引导',
      ...formatBooleanBadge(system.auto_bootstrap, '已启用', '已关闭'),
    },
    {
      label: '启动迁移',
      value: runMigrationsOnStartup ? '自动升级' : '显式迁移',
      variant: runMigrationsOnStartup ? 'secondary' : 'outline',
    },
    {
      label: '基础数据初始化',
      ...formatBooleanBadge(seedBaseDataOnStartup, '自动初始化', '手动初始化'),
    },
    {
      label: 'API 元数据刷新',
      ...formatBooleanBadge(refreshApiMetadataOnStartup, '自动刷新', '按需刷新'),
    },
  ]

  if (loading && !overview) {
    return <DashboardSkeleton />
  }

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-4 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">{system.app_title || system.title || 'React FastAPI Admin'}</h1>
          <p className="text-sm text-muted-foreground">
            系统概览、运行状态、分布图表和最近操作都集中在这里，便于快速判断当前活跃度。
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={environmentVariant}>环境 {environment}</Badge>
          <Badge variant="outline">版本 {system.version || '0.0.0'}</Badge>
          <Badge variant="outline">数据库 {system.database || 'sqlite'}</Badge>
          <Button variant="outline" onClick={() => setRefreshTick((currentTick) => currentTick + 1)}>
            <RefreshCcwIcon data-icon="inline-start" className={cn(loading && 'animate-spin')} />
            刷新数据
          </Button>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {statistics.map((item) => {
          const MetricIcon = item.icon

          return (
            <Card key={item.key}>
              <CardHeader className="pb-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-col gap-2">
                    <CardDescription>{item.title}</CardDescription>
                    <CardTitle className="text-2xl">{item.value}</CardTitle>
                  </div>
                  <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                    <MetricIcon />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-sm text-muted-foreground">{item.extra}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.72fr_1.28fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <div className="flex flex-col gap-1">
                <CardTitle>框架状态</CardTitle>
                <CardDescription>当前运行配置</CardDescription>
              </div>
              <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <DatabaseIcon />
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 pt-0">
            {systemStatusItems.map((item, index) => (
              <div
                key={`${item.label}-${index}`}
                className="flex items-center justify-between gap-3 border-b pb-3 last:border-b-0 last:pb-0"
              >
                <span className="text-sm text-muted-foreground">{item.label}</span>
                <Badge variant={item.variant}>{item.value}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <div className="flex flex-col gap-1">
                <CardTitle>近 7 天操作趋势</CardTitle>
                <CardDescription>使用折线展示最近一周的审计活跃度</CardDescription>
              </div>
              <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <WaypointsIcon />
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <TrendLineChart items={auditTrend} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <div className="flex flex-col gap-1">
                <CardTitle>模块活跃分布</CardTitle>
                <CardDescription>{chartActivityTotal ? `最近 7 天共 ${chartActivityTotal} 条审计记录` : '最近一周模块热度'}</CardDescription>
              </div>
              <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <WebhookIcon />
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <DistributionChart
              items={moduleActivity}
              emptyIcon={WebhookIcon}
              emptyTitle="暂无模块分布"
              emptyDescription="最近一周还没有可用于统计的模块活跃数据。"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <div className="flex flex-col gap-1">
                <CardTitle>状态码分布</CardTitle>
                <CardDescription>观察成功、异常和服务错误的占比变化</CardDescription>
              </div>
              <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <ShieldCheckIcon />
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <DistributionChart
              items={statusDistribution}
              emptyIcon={ShieldCheckIcon}
              emptyTitle="暂无状态分布"
              emptyDescription="最近一周还没有可展示的状态码统计。"
              renderLeading={(item) => (
                <Badge variant={item.badgeVariant}>{item.key}</Badge>
              )}
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div className="flex flex-col gap-1">
              <CardTitle>最近操作</CardTitle>
              <CardDescription>最新审计记录</CardDescription>
            </div>
            <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <ActivityIcon />
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {recentActivities.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用户</TableHead>
                  <TableHead>模块</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>耗时</TableHead>
                  <TableHead>时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentActivities.slice(0, 8).map((activity) => (
                  <TableRow key={activity.id}>
                    <TableCell className="font-medium">{activity.username || 'system'}</TableCell>
                    <TableCell>{activity.module || '基础模块'}</TableCell>
                    <TableCell className="max-w-[20rem] truncate">{activity.action}</TableCell>
                    <TableCell>
                      <Badge variant={resolveHttpStatusVariant(activity.status)}>
                        {activity.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{activity.response_time || 0} ms</TableCell>
                    <TableCell className="text-muted-foreground">{activity.created_at || activity.time || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <Empty className="border bg-muted/20 py-8">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <ActivityIcon />
                </EmptyMedia>
                <EmptyTitle>暂无操作记录</EmptyTitle>
                <EmptyDescription>最近活动列表为空，说明当前环境还没有新的审计数据。</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default Dashboard
