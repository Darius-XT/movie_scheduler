export const backupTables = [
  { key: 'movies', label: '电影' },
  { key: 'cinemas', label: '影院' },
  { key: 'movie_shows', label: '场次' },
  { key: 'planning_items', label: '行程' },
]

export const parseBackupFile = (text) => {
  let backup
  try {
    backup = JSON.parse(text.replace(/^\uFEFF/, ''))
  } catch {
    throw new Error('文件不是有效的 JSON，请选择本应用导出的备份文件')
  }
  if (backup?.success !== true || backup?.data?.application !== 'movie-scheduler') {
    throw new Error('文件不是 Movie Scheduler 数据备份')
  }
  if (backup.data.format_version !== 1) {
    throw new Error('暂不支持此备份格式版本，请使用兼容版本的应用导入')
  }
  if (typeof backup.data.exported_at !== 'string' || Number.isNaN(Date.parse(backup.data.exported_at))) {
    throw new Error('备份缺少有效的导出时间')
  }
  if (backupTables.some(({ key }) => !Array.isArray(backup.data[key]))) {
    throw new Error('备份不完整，必须包含电影、影院、场次和行程四张表')
  }
  return backup
}
