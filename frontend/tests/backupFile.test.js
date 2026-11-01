import assert from 'node:assert/strict'
import { test } from 'node:test'
import { backupTables, parseBackupFile } from '../src/utils/backupFile.js'

const backup = () => ({
  success: true,
  data: {
    application: 'movie-scheduler', format_version: 1, exported_at: '2026-11-02T12:00:00+08:00',
    movies: [{ id: -123, title: '手动电影' }], cinemas: [], movie_shows: [], planning_items: [],
  },
})

test('备份预览保留原始数据并支持 UTF-8 BOM', () => {
  const document = backup()
  assert.deepEqual(parseBackupFile(JSON.stringify(document)), document)
  assert.deepEqual(parseBackupFile('\uFEFF' + JSON.stringify(document)), document)
  assert.equal(backupTables.length, 4)
})

test('拒绝无效 JSON、其他应用、未知版本和不完整文件', () => {
  for (const text of ['', '{', 'null', '[]', '{}']) assert.throws(() => parseBackupFile(text))
  for (const changes of [
    { application: 'other' }, { format_version: 2 }, { format_version: true },
    { exported_at: null }, { exported_at: 'invalid' }, { movies: null }, { cinemas: {} },
  ]) {
    const document = backup()
    Object.assign(document.data, changes)
    assert.throws(() => parseBackupFile(JSON.stringify(document)))
  }
  const document = backup()
  delete document.data.planning_items
  assert.throws(() => parseBackupFile(JSON.stringify(document)))
  document.success = false
  assert.throws(() => parseBackupFile(JSON.stringify(document)))
})

test('允许完整的空备份，由覆盖确认决定是否清空', () => {
  const document = backup()
  document.data.movies = []
  assert.deepEqual(parseBackupFile(JSON.stringify(document)), document)
})
