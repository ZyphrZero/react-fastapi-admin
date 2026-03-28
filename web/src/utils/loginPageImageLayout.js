export const LOGIN_PAGE_IMAGE_MIN_ZOOM = 1
export const LOGIN_PAGE_IMAGE_MAX_ZOOM = 3
export const LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM = Object.freeze({
  zoom: 1,
  positionX: 50,
  positionY: 50,
})

const clamp = (value, min, max) => Math.min(Math.max(value, min), max)

const roundTo = (value, digits = 2) => {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}

export const normalizeLoginPageImageTransform = (value = {}) => {
  const zoom = Number(value.zoom)
  const positionX = Number(value.positionX)
  const positionY = Number(value.positionY)

  return {
    zoom: roundTo(clamp(Number.isFinite(zoom) ? zoom : LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM.zoom, LOGIN_PAGE_IMAGE_MIN_ZOOM, LOGIN_PAGE_IMAGE_MAX_ZOOM)),
    positionX: roundTo(clamp(Number.isFinite(positionX) ? positionX : LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM.positionX, 0, 100)),
    positionY: roundTo(clamp(Number.isFinite(positionY) ? positionY : LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM.positionY, 0, 100)),
  }
}

export const getLoginPageImageLayout = ({
  frameWidth,
  frameHeight,
  imageWidth,
  imageHeight,
  mode = 'contain',
  zoom = LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM.zoom,
  positionX = LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM.positionX,
  positionY = LOGIN_PAGE_IMAGE_DEFAULT_TRANSFORM.positionY,
}) => {
  if (!frameWidth || !frameHeight || !imageWidth || !imageHeight || mode === 'repeat') {
    return null
  }

  const normalized = normalizeLoginPageImageTransform({ zoom, positionX, positionY })
  let baseWidth = frameWidth
  let baseHeight = frameHeight

  if (mode === 'cover' || mode === 'contain') {
    const scale =
      mode === 'cover'
        ? Math.max(frameWidth / imageWidth, frameHeight / imageHeight)
        : Math.min(frameWidth / imageWidth, frameHeight / imageHeight)

    baseWidth = imageWidth * scale
    baseHeight = imageHeight * scale
  }

  const width = baseWidth * normalized.zoom
  const height = baseHeight * normalized.zoom
  const availableX = frameWidth - width
  const availableY = frameHeight - height
  const x = availableX * (normalized.positionX / 100)
  const y = availableY * (normalized.positionY / 100)

  return {
    width,
    height,
    x,
    y,
    availableX,
    availableY,
  }
}

export const getLoginPageImagePositionPercentFromOffset = (offset, availableSpace, fallback = 50) => {
  if (!Number.isFinite(availableSpace) || Math.abs(availableSpace) < 0.0001) {
    return fallback
  }

  return roundTo(clamp((offset / availableSpace) * 100, 0, 100))
}

export const buildLoginPageImageRepeatStyle = (src, { zoom, positionX, positionY } = {}) => {
  const normalized = normalizeLoginPageImageTransform({ zoom, positionX, positionY })

  return {
    backgroundImage: `url("${src}")`,
    backgroundPosition: `${normalized.positionX}% ${normalized.positionY}%`,
    backgroundRepeat: 'repeat',
    backgroundSize: `${Math.max(48, Math.round(160 * normalized.zoom))}px auto`,
  }
}
