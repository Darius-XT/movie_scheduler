const MINUTES_PER_DAY = 24 * 60
export const UNKNOWN_SHOW_DURATION_MINUTES = 180

export const parseShowTimeToMinutes = (timeText) => {
  const normalized = String(timeText ?? '').trim()
  const match = normalized.match(/^(\d{1,2}):(\d{2})$/)
  if (!match) return null

  const hours = Number(match[1])
  const minutes = Number(match[2])
  if (
    Number.isNaN(hours)
    || Number.isNaN(minutes)
    || hours < 0
    || hours > 23
    || minutes < 0
    || minutes > 59
  ) {
    return null
  }

  return hours * 60 + minutes
}

const formatMinutesAsTime = (totalMinutes) => {
  const wrappedMinutes = ((totalMinutes % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY
  const hours = Math.floor(wrappedMinutes / 60)
  const minutes = wrappedMinutes % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

export const formatShowTimeRange = (timeText, durationMinutes) => {
  const normalized = String(timeText ?? '').trim()
  const startMinutes = parseShowTimeToMinutes(normalized)
  if (startMinutes == null) return normalized

  if (typeof durationMinutes !== 'number' || Number.isNaN(durationMinutes) || durationMinutes <= 0) {
    return `${normalized}-\u672a\u77e5`
  }

  return `${normalized}-${formatMinutesAsTime(startMinutes + durationMinutes)}`
}

export const getShowDurationMinutes = (durationMinutes) => {
  if (typeof durationMinutes === 'number' && !Number.isNaN(durationMinutes) && durationMinutes > 0) {
    return durationMinutes
  }
  return UNKNOWN_SHOW_DURATION_MINUTES
}

export const getShowEndDate = (dateText, timeText, durationMinutes) => {
  const normalizedDate = String(dateText ?? '').trim()
  const dateMatch = normalizedDate.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  const startMinutes = parseShowTimeToMinutes(timeText)
  if (!dateMatch || startMinutes == null) return null

  const year = Number(dateMatch[1])
  const month = Number(dateMatch[2])
  const day = Number(dateMatch[3])
  const startDate = new Date(year, month - 1, day, 0, startMinutes)
  if (Number.isNaN(startDate.getTime())) return null
  if (
    startDate.getFullYear() !== year
    || startDate.getMonth() !== month - 1
    || startDate.getDate() !== day
  ) {
    return null
  }

  return new Date(startDate.getTime() + getShowDurationMinutes(durationMinutes) * 60 * 1000)
}
