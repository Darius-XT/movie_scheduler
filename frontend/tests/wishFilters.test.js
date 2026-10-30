import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getMovieViewingGroup, getMovieYear, matchesMovieChannel, MOVIE_CHANNELS } from '../src/utils/wishFilters.js'

test('按手动选择分组，年份不再决定观看地点', () => {
  assert.equal(getMovieViewingGroup({ release_date: '2026-01-01' }), 'unclassified')
  assert.equal(getMovieViewingGroup({ release_date: '1990-01-01' }), 'unclassified')
  assert.equal(getMovieViewingGroup({ viewing_location: 'home' }), 'home')
  assert.equal(getMovieViewingGroup({ viewing_location: 'cinema' }), 'cinema')
  assert.equal(getMovieViewingGroup({ viewing_location: null }), 'unclassified')
  assert.equal(getMovieYear({ release_date: '待定' }), null)
})

test('暂无默认收录无渠道电影，单渠道电影仅出现在对应分类', () => {
  assert.equal(matchesMovieChannel({}, 'none'), true)
  assert.equal(matchesMovieChannel({ channels: [] }, 'all'), true)
  const movie = { channels: ['bilibili'] }
  assert.equal(matchesMovieChannel(movie, 'all'), true)
  assert.equal(matchesMovieChannel(movie, 'none'), false)
  assert.equal(matchesMovieChannel(movie, 'bilibili'), true)
  assert.equal(matchesMovieChannel(movie, 'iqiyi'), false)
  assert.equal(matchesMovieChannel(movie, 'youku'), false)
  assert.deepEqual(MOVIE_CHANNELS.map((item) => item.label), ['b 站', '特狗', '电影天堂', '腾讯', '爱奇艺', '优酷'])
})
