import { useEffect, useState } from 'react'
import {
  ActivityIcon,
  ShieldCheckIcon,
  UsersIcon,
  WaypointsIcon,
  WebhookIcon,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  XAxis,
  YAxis,
} from 'recharts'

import api from '@/api'
import { Badge } from '@/components/ui/badge'
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
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const statusDistributionStyleMap = {
  '2xx': {
    badgeVariant: 'secondary',
    color: 'var(--color-chart-2)',
  },
  '3xx': {
    badgeVariant: 'outline',
    color: 'var(--color-chart-4)',
  },
  '4xx': {
    badgeVariant: 'outline',
    color: 'var(--color-chart-5)',
  },
  '5xx': {
    badgeVariant: 'destructive',
    color: 'var(--destructive)',
  },
  other: {
    badgeVariant: 'outline',
    color: 'var(--color-chart-3)',
  },
}

const moduleActivityPalette = [
  'var(--color-chart-1)',
  'var(--color-chart-2)',
  'var(--color-chart-3)',
  'var(--color-chart-4)',
  'var(--color-chart-5)',
]

const resolveHttpStatusVariant = (status) => {
  if (status >= 500) {
    return 'destructive'
  }

  if (status >= 400) {
    return 'outline'
  }

  return 'secondary'
}

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

const trendChartConfig = {
  count: {
    label: '操作量',
    color: 'var(--color-chart-1)',
  },
  average: {
    label: '日均基线',
    color: 'var(--color-chart-4)',
  },
}

const distributionChartConfig = {
  count: {
    label: '记录数',
    color: 'var(--color-chart-2)',
  },
}

const truncateAxisLabel = (value, maxLength = 10) => {
  if (!value) {
    return '--'
  }

  const text = String(value)
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text
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

    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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
        <Skeleton className="h-80 rounded-xl" />
      </CardContent>
    </Card>

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

  const totalCount = items.reduce((sum, item) => sum + item.count, 0)
  const averageCount = items.length ? Math.round(totalCount / items.length) : 0
  const peakItem = items.reduce((currentPeak, item) => {
    if (!currentPeak || item.count > currentPeak.count) {
      return item
      }
      return currentPeak
  }, null)
  const chartData = items.map((item) => ({
    ...item,
    average: averageCount,
  }))

  return (
    <div className="flex h-full w-full flex-col gap-4">
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

      <ChartContainer config={trendChartConfig} className="h-72 w-full flex-1 rounded-xl border bg-muted/10 p-4 xl:min-h-80">
        <AreaChart data={chartData} margin={{ left: 8, right: 8, top: 12, bottom: 8 }}>
          <defs>
            <linearGradient id="dashboard-audit-trend-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="var(--color-count)" stopOpacity="0.28" />
              <stop offset="100%" stopColor="var(--color-count)" stopOpacity="0.04" />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={false}
            minTickGap={18}
            tickFormatter={formatShortDateLabel}
          />
          <YAxis tickLine={false} axisLine={false} width={36} allowDecimals={false} />
          <ChartTooltip
            cursor={false}
            content={
              <ChartTooltipContent
                indicator="line"
                labelFormatter={(_, payload) => formatShortDateLabel(payload?.[0]?.payload?.date)}
                valueFormatter={(value) => `${value} 次`}
              />
            }
          />
          {averageCount > 0 ? (
            <ReferenceLine
              y={averageCount}
              stroke="var(--color-average)"
              strokeDasharray="4 4"
              ifOverflow="extendDomain"
            />
          ) : null}
          <Area
            type="monotone"
            dataKey="count"
            stroke="var(--color-count)"
            fill="url(#dashboard-audit-trend-fill)"
            strokeWidth={2.5}
            dot={{ r: 3, fill: 'var(--color-count)' }}
            activeDot={{ r: 5 }}
          />
        </AreaChart>
      </ChartContainer>
    </div>
  )
}

const DistributionChart = ({
  items,
  emptyIcon: EmptyIcon,
  emptyTitle,
  emptyDescription,
  colorResolver,
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

  const chartData = items.map((item, index) => ({
    ...item,
    fill: colorResolver?.(item, index) || moduleActivityPalette[index % moduleActivityPalette.length],
    shortLabel: truncateAxisLabel(item.label),
  }))

  return (
    <ChartContainer config={distributionChartConfig} className="h-80 w-full">
        <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 32, top: 4, bottom: 4 }} barCategoryGap={14}>
        <CartesianGrid horizontal={false} />
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="shortLabel"
          tickLine={false}
          axisLine={false}
          width={94}
        />
        <ChartTooltip
          cursor={false}
          content={
            <ChartTooltipContent
              hideIndicator
              labelFormatter={(_, payload) => payload?.[0]?.payload?.label || '--'}
              valueFormatter={(value, _, item) => `${value} ${countSuffix} · 占比 ${item.payload.share}%`}
            />
          }
        />
        <Bar dataKey="count" radius={8} barSize={22}>
          {chartData.map((item) => (
            <Cell key={item.key || item.label} fill={item.fill} />
          ))}
          <LabelList
            dataKey="count"
            position="right"
            offset={10}
            className="fill-foreground text-xs font-medium"
            formatter={(value) => `${value}`}
          />
        </Bar>
      </BarChart>
    </ChartContainer>
  )
}

const Dashboard = () => {
  const [loading, setLoading] = useState(false)
  const [overview, setOverview] = useState(null)

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
        console.error('Failed to fetch overview data:', error)

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
  }, [])

  const summary = overview?.summary || {}
  const system = overview?.system || {}
  const charts = overview?.charts || {}
  const auditTrend = overview?.audit_trend || []
  const recentActivities = overview?.recent_activities || []
  const moduleActivity = (charts.module_activity || []).map((item, index) => ({
    ...item,
    color: moduleActivityPalette[index % moduleActivityPalette.length],
  }))
  const statusDistribution = (charts.status_distribution || []).map((item) => ({
    ...item,
    badgeVariant: statusDistributionStyleMap[item.key]?.badgeVariant || 'outline',
    color: statusDistributionStyleMap[item.key]?.color || 'var(--color-chart-2)',
  }))
  const environment = system.environment || 'unknown'
  const environmentVariant = String(environment).toLowerCase() === 'prod' ? 'destructive' : 'secondary'
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

  if (loading && !overview) {
    return <DashboardSkeleton />
  }

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-4 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">{system.app_title || 'React Go Admin'}</h1>
          <p className="text-sm text-muted-foreground">
            系统概览、运行状态、分布图表和最近操作都集中在这里，便于快速判断当前活跃度。
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={environmentVariant}>环境 {environment}</Badge>
          <Badge variant="outline">版本 {system.version || '0.0.0'}</Badge>
          <Badge variant="outline">数据库 {system.database || 'sqlite'}</Badge>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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
              colorResolver={(item) => item.color}
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
              colorResolver={(item) => item.color}
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
                    <TableCell className="text-muted-foreground">{activity.created_at || '-'}</TableCell>
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
