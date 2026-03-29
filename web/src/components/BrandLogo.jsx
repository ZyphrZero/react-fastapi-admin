import { cn } from '@/lib/utils'

const BrandMark = ({ className }) => (
  <svg
    viewBox="0 0 64 64"
    aria-hidden="true"
    className={cn('size-10 shrink-0', className)}
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <linearGradient id="brand-logo-paper" x1="10" y1="8" x2="54" y2="58" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FFFDF8" />
        <stop offset="0.58" stopColor="#FFF2F6" />
        <stop offset="1" stopColor="#FFF0D8" />
      </linearGradient>
      <radialGradient id="brand-logo-blush" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(21 19) rotate(24) scale(24 16)">
        <stop stopColor="#FB7185" stopOpacity="0.4" />
        <stop offset="1" stopColor="#FB7185" stopOpacity="0" />
      </radialGradient>
      <radialGradient id="brand-logo-amber" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(45 43) rotate(-12) scale(20 15)">
        <stop stopColor="#F59E0B" stopOpacity="0.34" />
        <stop offset="1" stopColor="#F59E0B" stopOpacity="0" />
      </radialGradient>
      <linearGradient id="brand-logo-stroke-main" x1="18" y1="19" x2="47" y2="41" gradientUnits="userSpaceOnUse">
        <stop stopColor="#B44E77" />
        <stop offset="0.58" stopColor="#F08DB5" />
        <stop offset="1" stopColor="#F5AE42" />
      </linearGradient>
      <linearGradient id="brand-logo-highlight" x1="18" y1="18" x2="43" y2="31" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FFFFFF" stopOpacity="0.88" />
        <stop offset="1" stopColor="#FFFFFF" stopOpacity="0" />
      </linearGradient>
      <filter id="brand-logo-soft" x="7" y="7" width="50" height="50" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
        <feGaussianBlur stdDeviation="4.6" />
      </filter>
      <filter id="brand-logo-shadow" x="11" y="13" width="42" height="36" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
        <feDropShadow dx="0" dy="2.6" stdDeviation="2.4" floodColor="#B85A7F" floodOpacity="0.17" />
      </filter>
    </defs>

    <rect x="6" y="6" width="52" height="52" rx="17" fill="url(#brand-logo-paper)" />
    <ellipse cx="23" cy="22" rx="13.5" ry="9.8" fill="url(#brand-logo-blush)" filter="url(#brand-logo-soft)" opacity="0.95" />
    <ellipse cx="43.5" cy="41.5" rx="12" ry="8.8" fill="url(#brand-logo-amber)" filter="url(#brand-logo-soft)" opacity="0.92" />
    <path
      d="M18.4 21.4C25.6 17.9 33.4 18.1 40.9 20.2C44.1 21.1 45.2 24 43.3 26.2L32.6 37.9C31.1 39.5 31.8 41.8 34 41.8C37.6 41.7 41.2 40.6 45.6 38.5"
      stroke="url(#brand-logo-shadow-stroke)"
      strokeWidth="10"
      strokeLinecap="round"
      strokeLinejoin="round"
      opacity="0.52"
    />
    <path
      d="M18.4 20C25.6 16.5 33.4 16.7 40.9 18.8C44.1 19.7 45.2 22.6 43.3 24.8L32.6 36.5C31.1 38.1 31.8 40.4 34 40.4C37.6 40.3 41.2 39.2 45.6 37.1"
      stroke="url(#brand-logo-stroke-main)"
      strokeWidth="9"
      strokeLinecap="round"
      strokeLinejoin="round"
      filter="url(#brand-logo-shadow)"
    />
    <path
      d="M21.2 19.1C27 17.2 33 17.1 38.6 18.4C40.8 18.9 41.6 20.7 40.6 22.2L34.3 29.3"
      stroke="url(#brand-logo-highlight)"
      strokeWidth="2.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      opacity="0.86"
    />
  </svg>
)

const BrandLogo = ({
  className,
  markClassName,
  titleClassName,
  subtitleClassName,
  title = 'React Go Admin',
  subtitle = 'CONTROL CENTER',
  compact = false,
}) => (
  <div className={cn('flex items-center gap-3', className)}>
    <BrandMark className={markClassName} />
    {!compact ? (
      <div className="grid min-w-0 leading-none">
        <span className={cn('truncate text-sm font-semibold tracking-[-0.02em] text-foreground', titleClassName)}>{title}</span>
        <span className={cn('truncate text-[10px] uppercase tracking-[0.28em] text-muted-foreground', subtitleClassName)}>{subtitle}</span>
      </div>
    ) : null}
  </div>
)

export default BrandLogo
