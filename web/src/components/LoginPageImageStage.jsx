import { useState } from 'react'

import { cn } from '@/lib/utils'

const defaultLoginPageImage = '/login-panel-illustration.svg'

const objectModeClassMap = {
  cover: 'object-cover',
  contain: 'object-contain',
  fill: 'object-fill',
}

const LoginPageImageStageInner = ({
  resolvedSrc,
  mode,
  fillParent,
  alt,
  className,
  frameClassName,
  imageClassName,
}) => {
  const [fallbackActive, setFallbackActive] = useState(false)
  const currentSrc = fallbackActive ? defaultLoginPageImage : resolvedSrc

  return (
    <div className={cn('flex w-full max-w-[30rem] items-center justify-center', className)}>
      <div
        className={cn(
          'flex w-full items-center justify-center overflow-hidden rounded-[1.8rem]',
          fillParent ? 'h-full' : 'aspect-[16/10]',
          frameClassName
        )}
        style={
          mode === 'repeat'
            ? {
                backgroundImage: `url("${currentSrc}")`,
                backgroundPosition: 'center',
                backgroundRepeat: 'repeat',
                backgroundSize: '160px auto',
              }
            : undefined
        }
      >
        {mode !== 'repeat' ? (
          <img
            src={currentSrc}
            alt={alt}
            className={cn('h-full w-full select-none', objectModeClassMap[mode] || objectModeClassMap.contain, imageClassName)}
            onError={(event) => {
              if (event.currentTarget.src !== defaultLoginPageImage) {
                event.currentTarget.src = defaultLoginPageImage
                setFallbackActive(true)
              }
            }}
          />
        ) : null}
      </div>
    </div>
  )
}

const LoginPageImageStage = ({
  src,
  mode = 'contain',
  alt = '后台管理登录展示图',
  fillParent = false,
  className,
  frameClassName,
  imageClassName,
}) => {
  const resolvedSrc = src?.trim() || defaultLoginPageImage
  const resolvedMode = mode === 'repeat' ? 'repeat' : objectModeClassMap[mode] ? mode : 'contain'

  return (
    <LoginPageImageStageInner
      key={`${resolvedSrc}:${resolvedMode}`}
      resolvedSrc={resolvedSrc}
      mode={resolvedMode}
      fillParent={fillParent}
      alt={alt}
      className={cn(fillParent ? 'h-full max-w-none' : undefined, className)}
      frameClassName={cn(fillParent ? 'h-full w-full rounded-none' : undefined, frameClassName)}
      imageClassName={imageClassName}
    />
  )
}

export { LoginPageImageStage }
