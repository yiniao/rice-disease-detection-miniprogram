function pad(value) {
  return String(value).padStart(2, '0')
}

function formatDisplayTime(value) {
  const raw = String(value || '').trim()
  if (!raw) {
    return '时间未知'
  }

  const matched = raw.match(
    /^(\d{4}-\d{2}-\d{2})[T\s](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d+))?)?(Z|[+-]\d{2}:?\d{2})?/
  )
  if (!matched) {
    return '时间未知'
  }

  const [, datePart, hours, minutes, seconds = '00', fraction = '', timezone = ''] = matched
  const [year, month, day] = datePart.split('-').map(Number)
  const sourceHours = Number(hours)
  const sourceMinutes = Number(minutes)
  const sourceSeconds = Number(seconds)
  const milliseconds = Number(fraction.slice(0, 3).padEnd(3, '0'))

  // Django normally returns UTC timestamps. Values without a timezone are
  // treated as Beijing time so display is independent of device timezone.
  let sourceOffsetMinutes = 8 * 60
  if (timezone === 'Z') {
    sourceOffsetMinutes = 0
  } else if (timezone) {
    const offsetMatch = timezone.match(/^([+-])(\d{2}):?(\d{2})$/)
    if (offsetMatch) {
      const offsetMinutes = Number(offsetMatch[2]) * 60 + Number(offsetMatch[3])
      sourceOffsetMinutes = offsetMatch[1] === '+' ? offsetMinutes : -offsetMinutes
    }
  }

  const timestamp = Date.UTC(
    year,
    month - 1,
    day,
    sourceHours,
    sourceMinutes,
    sourceSeconds,
    milliseconds
  ) - sourceOffsetMinutes * 60 * 1000
  const beijingTime = new Date(timestamp + 8 * 60 * 60 * 1000)

  if (Number.isNaN(beijingTime.getTime())) {
    return '时间未知'
  }

  return [
    beijingTime.getUTCFullYear(),
    pad(beijingTime.getUTCMonth() + 1),
    pad(beijingTime.getUTCDate())
  ].join('-') + ` ${pad(beijingTime.getUTCHours())}:${pad(beijingTime.getUTCMinutes())}`
}

module.exports = {
  formatDisplayTime
}
