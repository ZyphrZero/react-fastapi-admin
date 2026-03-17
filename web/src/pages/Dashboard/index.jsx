import { useEffect, useState } from 'react'
import {
  ActivityIcon,
  DatabaseIcon,
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

const readinessToneMap = {
  success: {
    badgeVariant: 'secondary',
    accentClassName: 'bg-emerald-500/14 text-emerald-700 ring-emerald-500/20 dark:text-emerald-300',
    dotClassName: 'bg-emerald-500',
  },
  warn: {
    badgeVariant: 'outline',
    accentClassName: 'bg-amber-500/12 text-amber-700 ring-amber-500/20 dark:text-amber-300',
    dotClassName: 'bg-amber-500',
  },
  info: {
    badgeVariant: 'outline',
    accentClassName: 'bg-sky-500/12 text-sky-700 ring-sky-500/20 dark:text-sky-300',
    dotClassName: 'bg-sky-500',
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

const FrameworkStatusPanel = ({ items, environment }) => {
  const completedCount = items.filter((item) => item.valueTone === 'success').length
  const warnCount = items.filter((item) => item.valueTone === 'warn').length
  const readinessValue = items.length > 0 ? Math.round((completedCount / items.length) * 100) : 0
  const readinessTone = warnCount > 0 ? 'warn' : 'success'
  const readinessMeta = readinessToneMap[readinessTone]

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_11rem]">
        <div className={`rounded-2xl border p-4 ring-1 ${readinessMeta.accentClassName}`}>
          <div className="flex items-center justify-between gap-3">
            <div className="flex flex-col gap-1">
              <div className="text-xs font-medium uppercase tracking-[0.18em] opacity-80">系统就绪度</div>
              <div className="text-3xl font-semibold tabular-nums">{readinessValue}%</div>
            </div>
            <Badge variant={readinessMeta.badgeVariant}>{environment}</Badge>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-background/60">
            <div className="h-full rounded-full bg-current transition-[width]" style={{ width: `${readinessValue}%` }} />
          </div>
          <div className="mt-3 text-sm opacity-85">
            {warnCount > 0 ? `存在 ${warnCount} 项需要留意` : '当前核心能力均处于可用状态'}
          </div>
        </div>

        <div className="rounded-2xl border bg-muted/20 p-4">
          <div className="text-xs text-muted-foreground">配置摘要</div>
          <div className="mt-3 grid gap-3">
            <div>
              <div className="text-2xl font-semibold tabular-nums">{completedCount}</div>
              <div className="text-xs text-muted-foreground">正常项</div>
            </div>
            <div>
              <div className="text-2xl font-semibold tabular-nums">{warnCount}</div>
              <div className="text-xs text-muted-foreground">关注项</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-3">
        {items.map((item, index) => {
          const tone = readinessToneMap[item.valueTone] || readinessToneMap.info

          return (
            <div
              key={`${item.label}-${index}`}
              className="grid gap-2 rounded-2xl border bg-card/80 p-4 sm:grid-cols-[10rem_minmax(0,1fr)_auto] sm:items-center"
            >
              <div className="text-sm text-muted-foreground">{item.label}</div>
              <div className="flex items-center gap-3">
                <span className={`size-2.5 rounded-full ${tone.dotClassName}`} />
                <div className="min-w-0">
                  <div className="font-medium">{item.value}</div>
                  <div className="text-xs text-muted-foreground">{item.description}</div>
                </div>
              </div>
              <Badge variant={tone.badgeVariant}>{item.badgeText}</Badge>
            </div>
          )
        })}
      </div>
    </div>
  )
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

      <ChartContainer config={trendChartConfig} className="h-64 w-full rounded-xl border bg-muted/10 p-4">
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
                formatter={(value) => `${value} 次`}
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
              formatter={(value, _, item) => `${value} ${countSuffix} · 占比 ${item.payload.share}%`}
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
  const environmentVariant = String(environment).toLowerCase() === 'production' ? 'destructive' : 'secondary'
  const runMigrationsOnStartup = system.run_migrations_on_startup ?? false
  const seedBaseDataOnStartup = system.seed_base_data_on_startup ?? false
  const refreshApiMetadataOnStartup = system.refresh_api_metadata_on_startup ?? false
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
      description: environmentVariant === 'destructive' ? '生产环境，建议关注稳定性与审计数据' : '开发环境，适合快速验证与调试',
      badgeText: environmentVariant === 'destructive' ? '严格模式' : '调试模式',
      valueTone: environmentVariant === 'destructive' ? 'warn' : 'info',
    },
    {
      label: '数据库引擎',
      value: system.database || 'sqlite',
      description: '当前工作台概览与审计数据都依赖此连接提供。',
      badgeText: '核心依赖',
      valueTone: 'info',
    },
    {
      label: '访问日志',
      value: system.access_log_enabled ? '已启用' : '已关闭',
      description: system.access_log_enabled ? '每个请求都会保留访问轨迹。' : '请求轨迹不会写入访问日志。',
      badgeText: system.access_log_enabled ? '观测开启' : '观测关闭',
      valueTone: system.access_log_enabled ? 'success' : 'warn',
    },
    {
      label: '自动引导',
      value: system.auto_bootstrap ? '已启用' : '已关闭',
      description: system.auto_bootstrap ? '启动时会自动执行基础准备流程。' : '基础准备需要人工执行。',
      badgeText: system.auto_bootstrap ? '启动增强' : '手动模式',
      valueTone: system.auto_bootstrap ? 'success' : 'warn',
    },
    {
      label: '启动迁移',
      value: runMigrationsOnStartup ? '自动升级' : '显式迁移',
      description: runMigrationsOnStartup ? '实例启动时会自动应用数据库迁移。' : '数据库迁移需要显式执行。',
      badgeText: runMigrationsOnStartup ? '自动同步' : '谨慎控制',
      valueTone: runMigrationsOnStartup ? 'success' : 'warn',
    },
    {
      label: '基础数据初始化',
      value: seedBaseDataOnStartup ? '自动初始化' : '手动初始化',
      description: seedBaseDataOnStartup ? '默认角色和基础数据会在启动时补齐。' : '基础数据不会自动注入。',
      badgeText: seedBaseDataOnStartup ? '种子开启' : '种子关闭',
      valueTone: seedBaseDataOnStartup ? 'success' : 'warn',
    },
    {
      label: 'API 元数据刷新',
      value: refreshApiMetadataOnStartup ? '自动刷新' : '按需刷新',
      description: refreshApiMetadataOnStartup ? 'API 目录会在启动时自动同步。' : '接口目录依赖手动扫描更新。',
      badgeText: refreshApiMetadataOnStartup ? '目录同步' : '手动扫描',
      valueTone: refreshApiMetadataOnStartup ? 'success' : 'warn',
    },
  ]

  if (loading && !overview) {
    return <DashboardSkeleton />
  }

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-4 border-b pb-5 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">{system.app_title || 'React FastAPI Admin'}</h1>
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
          <CardContent className="pt-0">
            <FrameworkStatusPanel items={systemStatusItems} environment={environment} />
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
