import { useMemo, useRef, useState } from 'react'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'

const cropSize = 280
const outputSize = 512
const previewSize = 96
const minZoom = 1
const maxZoom = 3
const zoomStep = 0.08
const cropCircleRadius = cropSize / 2 - 4

const clamp = (value, min, max) => Math.min(Math.max(value, min), max)

const getBounds = (imageSize, scale) => {
  const scaledWidth = imageSize.width * scale
  const scaledHeight = imageSize.height * scale

  return {
    minX: Math.min(0, cropSize - scaledWidth),
    maxX: 0,
    minY: Math.min(0, cropSize - scaledHeight),
    maxY: 0,
  }
}

const clampOffset = (offset, imageSize, scale) => {
  if (!imageSize.width || !imageSize.height) {
    return offset
  }

  const bounds = getBounds(imageSize, scale)
  return {
    x: clamp(offset.x, bounds.minX, bounds.maxX),
    y: clamp(offset.y, bounds.minY, bounds.maxY),
  }
}

const getBaseScale = (imageSize) => {
  if (!imageSize.width || !imageSize.height) {
    return 1
  }

  return Math.max(cropSize / imageSize.width, cropSize / imageSize.height)
}

const getInitialOffset = (imageSize, scale) => {
  const scaledWidth = imageSize.width * scale
  const scaledHeight = imageSize.height * scale

  return clampOffset(
    {
      x: (cropSize - scaledWidth) / 2,
      y: (cropSize - scaledHeight) / 2,
    },
    imageSize,
    scale,
  )
}

const canvasToBlob = (canvas, type, quality) =>
  new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob)
        return
      }

      reject(new Error('无法生成头像文件'))
    }, type, quality)
  })

const AvatarEditorDialog = ({
  open,
  imageSrc,
  fallback,
  submitting = false,
  onOpenChange,
  onConfirm,
}) => {
  const imageRef = useRef(null)
  const dragStateRef = useRef(null)

  const [imageSize, setImageSize] = useState({ width: 0, height: 0 })
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })

  const baseScale = useMemo(() => getBaseScale(imageSize), [imageSize])
  const scale = baseScale * zoom
  const previewRatio = previewSize / cropSize

  const handleImageLoad = () => {
    const target = imageRef.current
    if (!target) {
      return
    }

    const nextImageSize = {
      width: target.naturalWidth,
      height: target.naturalHeight,
    }

    const nextScale = getBaseScale(nextImageSize)
    setImageSize(nextImageSize)
    setOffset(getInitialOffset(nextImageSize, nextScale))
    setZoom(1)
  }

  const handleZoomChange = (event) => {
    const nextZoom = clamp(Number(event.target.value), minZoom, maxZoom)
    setZoom(nextZoom)
    setOffset((current) => clampOffset(current, imageSize, baseScale * nextZoom))
  }

  const applyZoomAtPoint = (nextZoom, pointX, pointY) => {
    if (!imageSize.width || !imageSize.height) {
      return
    }

    const clampedZoom = clamp(nextZoom, minZoom, maxZoom)
    const nextScale = baseScale * clampedZoom
    const imagePointX = (pointX - offset.x) / scale
    const imagePointY = (pointY - offset.y) / scale

    setZoom(clampedZoom)
    setOffset(
      clampOffset(
        {
          x: pointX - imagePointX * nextScale,
          y: pointY - imagePointY * nextScale,
        },
        imageSize,
        nextScale,
      ),
    )
  }

  const handleWheel = (event) => {
    if (!imageSize.width || !imageSize.height) {
      return
    }

    event.preventDefault()

    const rect = event.currentTarget.getBoundingClientRect()
    const pointX = event.clientX - rect.left
    const pointY = event.clientY - rect.top
    const nextZoom = zoom + (event.deltaY < 0 ? zoomStep : -zoomStep)

    applyZoomAtPoint(nextZoom, pointX, pointY)
  }

  const handlePointerDown = (event) => {
    if (!imageSize.width || !imageSize.height) {
      return
    }

    dragStateRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      initialOffset: offset,
    }

    event.currentTarget.setPointerCapture(event.pointerId)
  }

  const handlePointerMove = (event) => {
    const dragState = dragStateRef.current
    if (!dragState || dragState.pointerId !== event.pointerId) {
      return
    }

    const deltaX = event.clientX - dragState.startX
    const deltaY = event.clientY - dragState.startY

    setOffset(
      clampOffset(
        {
          x: dragState.initialOffset.x + deltaX,
          y: dragState.initialOffset.y + deltaY,
        },
        imageSize,
        scale,
      ),
    )
  }

  const handlePointerUp = (event) => {
    if (dragStateRef.current?.pointerId === event.pointerId) {
      dragStateRef.current = null
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  const handleConfirm = async () => {
    const image = imageRef.current
    if (!image || !imageSize.width || !imageSize.height) {
      return
    }

    const canvas = document.createElement('canvas')
    canvas.width = outputSize
    canvas.height = outputSize

    const context = canvas.getContext('2d')
    if (!context) {
      throw new Error('无法初始化头像编辑画布')
    }

    context.clearRect(0, 0, outputSize, outputSize)

    const sourceWidth = cropSize / scale
    const sourceHeight = cropSize / scale
    const sourceX = -offset.x / scale
    const sourceY = -offset.y / scale

    context.drawImage(
      image,
      sourceX,
      sourceY,
      sourceWidth,
      sourceHeight,
      0,
      0,
      outputSize,
      outputSize,
    )

    const blob = await canvasToBlob(canvas, 'image/webp', 0.86)
    await onConfirm(blob)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[calc(100%-2rem)] p-0 sm:max-w-3xl">
        <DialogHeader className="px-6 pt-6">
          <DialogTitle>编辑头像</DialogTitle>
          <DialogDescription>拖动图片调整裁剪区域，保存时会自动转换为更小的 WebP 头像。</DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 px-6 pb-6 lg:grid-cols-[minmax(0,1fr)_15rem]">
          <div className="flex flex-col gap-4">
            <div
              className="relative size-[280px] touch-none overflow-hidden rounded-2xl border bg-muted/30 shadow-inner"
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={handlePointerUp}
              onPointerCancel={handlePointerUp}
              onWheel={handleWheel}
            >
              <img
                ref={imageRef}
                src={imageSrc}
                alt="待编辑头像"
                className="absolute top-0 left-0 max-w-none select-none"
                draggable={false}
                onLoad={handleImageLoad}
                style={{
                  width: imageSize.width ? imageSize.width * scale : 'auto',
                  height: imageSize.height ? imageSize.height * scale : 'auto',
                  transform: `translate(${offset.x}px, ${offset.y}px)`,
                  transformOrigin: 'top left',
                }}
              />
              <svg className="pointer-events-none absolute inset-0 size-full" viewBox={`0 0 ${cropSize} ${cropSize}`} aria-hidden="true">
                <defs>
                  <mask id="avatar-editor-mask">
                    <rect width={cropSize} height={cropSize} fill="white" />
                    <circle cx={cropSize / 2} cy={cropSize / 2} r={cropCircleRadius} fill="black" />
                  </mask>
                </defs>
                <rect width={cropSize} height={cropSize} fill="rgba(15, 23, 42, 0.34)" mask="url(#avatar-editor-mask)" />
                <circle
                  cx={cropSize / 2}
                  cy={cropSize / 2}
                  r={cropCircleRadius}
                  fill="none"
                  stroke="rgba(255,255,255,0.9)"
                  strokeWidth="3"
                />
                <circle
                  cx={cropSize / 2}
                  cy={cropSize / 2}
                  r={cropCircleRadius + 1.5}
                  fill="none"
                  stroke="rgba(15,23,42,0.12)"
                  strokeWidth="1"
                />
              </svg>
            </div>

            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>缩放</span>
                <span>{zoom.toFixed(2)}x</span>
              </div>
              <input
                type="range"
                min={String(minZoom)}
                max={String(maxZoom)}
                step="0.01"
                value={zoom}
                className="w-full accent-[hsl(var(--primary))]"
                onChange={handleZoomChange}
              />
            </div>
          </div>

          <div className="flex flex-col gap-4 rounded-2xl border bg-muted/20 p-4">
            <div className="text-sm font-medium">预览</div>
            <div className="flex items-center justify-center rounded-2xl bg-background p-6">
              <div className="relative size-24 overflow-hidden rounded-full bg-muted">
                <img
                  src={imageSrc}
                  alt="头像预览"
                  className="absolute top-0 left-0 max-w-none select-none"
                  draggable={false}
                  style={{
                    width: imageSize.width ? imageSize.width * scale * previewRatio : 'auto',
                    height: imageSize.height ? imageSize.height * scale * previewRatio : 'auto',
                    transform: `translate(${offset.x * previewRatio}px, ${offset.y * previewRatio}px)`,
                    transformOrigin: 'top left',
                  }}
                />
                {!imageSrc ? (
                  <Avatar size="lg" className="size-24">
                    <AvatarFallback>{fallback}</AvatarFallback>
                  </Avatar>
                ) : null}
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              建议头像主体居中放置，裁剪后会输出为 512 x 512 的 WebP 图片。
            </div>
          </div>
        </div>

        <DialogFooter className="mx-0 mb-0 rounded-b-xl px-6 py-4">
          <Button type="button" variant="outline" disabled={submitting} onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button type="button" disabled={submitting} onClick={() => void handleConfirm()}>
            {submitting ? '处理中...' : '保存头像'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default AvatarEditorDialog
