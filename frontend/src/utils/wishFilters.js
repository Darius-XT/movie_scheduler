export const MOVIE_CHANNELS = [
  { value: 'bilibili', label: 'b 站' },
  { value: 'tegou', label: '特狗' },
  { value: 'dytt', label: '电影天堂' },
  { value: 'tencent', label: '腾讯' },
  { value: 'iqiyi', label: '爱奇艺' },
  { value: 'youku', label: '优酷' },
]

export const getMovieYear = (movie) => {
  const match = String(movie?.release_date || '').trim().match(/^(\d{4})(?:\D|$)/)
  const year = match ? Number(match[1]) : null
  return year > 0 ? year : null
}

export const getMovieViewingGroup = (movie) => movie.viewing_location || 'unclassified'

export const matchesMovieChannel = (movie, channel) => {
  const channels = movie.channels || []
  if (channel === 'all') return true
  if (channel === 'none') return channels.length === 0
  return channels[0] === channel
}
