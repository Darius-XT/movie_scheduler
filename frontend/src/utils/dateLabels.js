const WEEKDAY_LABELS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const DAY_MS = 24 * 60 * 60 * 1000

const normalizeDate = (date) => {
  const normalized = new Date(date)
  normalized.setHours(0, 0, 0, 0)
  return normalized
}

const getWeekStart = (date) => {
  const normalized = normalizeDate(date)
  const weekday = normalized.getDay()
  const offset = weekday === 0 ? -6 : 1 - weekday
  normalized.setDate(normalized.getDate() + offset)
  return normalized
}

const parseShowDate = (dateText) => {
  if (!dateText) return null
  const parsed = new Date(`${dateText}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export const getWeekOffsetFromToday = (dateText) => {
  const targetDate = parseShowDate(dateText)
  if (!targetDate) return null
  const currentWeekStart = getWeekStart(new Date())
  const targetWeekStart = getWeekStart(targetDate)
  return Math.floor((targetWeekStart.getTime() - currentWeekStart.getTime()) / (7 * DAY_MS))
}

export const isInCurrentWeek = (dateText) => getWeekOffsetFromToday(dateText) === 0

export const isInNextWeek = (dateText) => getWeekOffsetFromToday(dateText) === 1

export const formatDateWithRelativeWeek = (dateText) => {
  if (!dateText) return ''
  const targetDate = parseShowDate(dateText)
  if (!targetDate) return dateText

  const today = normalizeDate(new Date())
  const targetDay = normalizeDate(targetDate)
  const diffDays = Math.round((targetDay.getTime() - today.getTime()) / DAY_MS)

  let suffix = ''
  if (diffDays === 0) suffix = '今天'
  else if (diffDays === 1) suffix = '明天'
  else if (diffDays === 2) suffix = '后天'
  else {
    const diffWeeks = getWeekOffsetFromToday(dateText) ?? 0
    if (diffWeeks <= 0) suffix = `本${WEEKDAY_LABELS[targetDate.getDay()]}`
    else if (diffWeeks === 1) suffix = `下${WEEKDAY_LABELS[targetDate.getDay()]}`
    else if (diffWeeks === 2) suffix = `下下${WEEKDAY_LABELS[targetDate.getDay()]}`
    else suffix = '三周后'
  }

  return `${dateText}（${suffix}）`
}
