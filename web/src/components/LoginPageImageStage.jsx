import { useEffect, useMemo, useRef, useState } from 'react'

import { cn } from '@/lib/utils'
import {
  buildLoginPageImageRepeatStyle,
  getLoginPageImageLayout,
  LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM,
  normalizeLoginPageImageTransform,
} from '@/utils/loginPageImageLayout'

const defaultLoginPageImage = '/login-panel-illustration.svg'

const LoginPageImageStageInner = ({
  resolvedSrc,
  mode,
  fillParent,
  alt,
  zoom,
  positionX,
  positionY,
  className,
  frameClassName,
  imageClassName,
}) => {
  const frameRef = useRef(null)
  const [fallbackActive, setFallbackActive] = useState(false)
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 })
  const [frameSize, setFrameSize] = useState({ width: 0, height: 0 })
  const currentSrc = fallbackActive ? defaultLoginPageImage : resolvedSrc
  const transform = useMemo(
    () => normalizeLoginPageImageTransform({ zoom, positionX, positionY }),
    [positionX, positionY, zoom]
  )
  const imageLayout = useMemo(
    () =>
      getLoginPageImageLayout({
        frameWidth: frameSize.width,
        frameHeight: frameSize.height,
        imageWidth: imageSize.width,
        imageHeight: imageSize.height,
        mode,
        zoom: transform.zoom,
        positionX: transform.positionX,
        positionY: transform.positionY,
      }),
    [frameSize.height, frameSize.width, imageSize.height, imageSize.width, mode, transform.positionX, transform.positionY, transform.zoom]
  )

  useEffect(() => {
    const frame = frameRef.current
    if (!frame) {
      return undefined
    }

    const updateFrameSize = () => {
      const nextWidth = frame.clientWidth
      const nextHeight = frame.clientHeight
      setFrameSize((current) =>
        current.width === nextWidth && current.height === nextHeight
          ? current
          : { width: nextWidth, height: nextHeight }
      )
    }

    updateFrameSize()

    const observer = new ResizeObserver(updateFrameSize)
    observer.observe(frame)
    return () => observer.disconnect()
  }, [])

  const handleImageLoad = (event) => {
    const target = event.currentTarget
    const nextImageSize = {
      width: target.naturalWidth,
      height: target.naturalHeight,
    }

    setImageSize((current) =>
      current.width === nextImageSize.width && current.height === nextImageSize.height ? current : nextImageSize
    )
  }

  const handleImageError = (event) => {
    if (event.currentTarget.src !== defaultLoginPageImage) {
      event.currentTarget.src = defaultLoginPageImage
      setFallbackActive(true)
    }
  }

  const imageStyle =
    mode === 'repeat'
      ? undefined
      : imageLayout
        ? {
            width: `${imageLayout.width}px`,
            height: `${imageLayout.height}px`,
            transform: `translate(${imageLayout.x}px, ${imageLayout.y}px)`,
            transformOrigin: 'top left',
          }
        : {
            inset: 0,
            width: '100%',
            height: '100%',
            objectFit: mode === 'fill' ? 'fill' : mode,
            objectPosition: `${transform.positionX}% ${transform.positionY}%`,
            transform: `scale(${transform.zoom})`,
            transformOrigin: 'center center',
          }

  return (
    <div
      className={cn(
        'flex w-full max-w-[30rem] items-center justify-center',
        fillParent ? 'h-full max-w-none min-h-0' : undefined,
        className
      )}
    >
      <div
        ref={frameRef}
        className={cn(
          'flex w-full items-center justify-center overflow-hidden rounded-[1.8rem]',
          fillParent ? 'relative h-full min-h-0' : 'aspect-[16/10]',
          frameClassName
        )}
        style={
          mode === 'repeat'
            ? buildLoginPageImageRepeatStyle(currentSrc, transform)
            : undefined
        }
      >
        {mode !== 'repeat' ? (
          <img
            src={currentSrc}
            alt={alt}
            className={cn('absolute top-0 left-0 max-w-none select-none', imageClassName)}
            draggable={false}
            onLoad={handleImageLoad}
            onError={handleImageError}
            style={imageStyle}
          />
        ) : (
          <img
            src={currentSrc}
            alt=""
            className="hidden"
            aria-hidden="true"
            onLoad={handleImageLoad}
            onError={handleImageError}
          />
        )}
      </div>
    </div>
  )
}

const LoginPageImageStage = ({
  src,
  mode = 'contain',
  alt = '后台管理登录展示图',
  fillParent = false,
  zoom = LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM.zoom,
  positionX = LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM.positionX,
  positionY = LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM.positionY,
  className,
  frameClassName,
  imageClassName,
}) => {
  const resolvedSrc = src?.trim() || defaultLoginPageImage
  const resolvedMode = ['cover', 'contain', 'fill', 'repeat'].includes(mode) ? mode : 'contain'

  return (
    <LoginPageImageStageInner
      key={`${resolvedSrc}:${resolvedMode}`}
      resolvedSrc={resolvedSrc}
      mode={resolvedMode}
      fillParent={fillParent}
      alt={alt}
      zoom={zoom}
      positionX={positionX}
      positionY={positionY}
      className={cn(fillParent ? 'h-full max-w-none' : undefined, className)}
      frameClassName={cn(fillParent ? 'h-full w-full rounded-none' : undefined, frameClassName)}
      imageClassName={imageClassName}
    />
  )
}

export { LoginPageImageStage }
