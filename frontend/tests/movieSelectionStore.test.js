import assert from 'node:assert/strict'
import { after, before, beforeEach, test } from 'node:test'
import { createServer } from 'vite'
import { createPinia, setActivePinia } from 'pinia'

let server
let useMovieSelectionStore
let api

before(async () => {
  globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} }
  server = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  ;({ useMovieSelectionStore } = await server.ssrLoadModule('/src/stores/movieSelectionStore.js'))
  ;({ default: api } = await server.ssrLoadModule('/src/api/index.js'))
})

after(async () => {
  await server?.close()
  delete globalThis.localStorage
})

beforeEach(() => setActivePinia(createPinia()))

const movie = { id: 123, title: '电影', is_wished: false, is_skipped: false, is_watched: false }

test('标签切换同步电影条目和想看列表，取消后恢复无标签', async () => {
  const store = useMovieSelectionStore()
  store.setSelectedMovies([{ ...movie }])
  api.defaults.adapter = async (config) => {
    const { label } = JSON.parse(config.data)
    assert.equal(config.url, '/movies/123/label')
    return {
      data: { success: true, data: { movie: { ...movie, is_wished: label === 'wished', is_skipped: label === 'skipped', is_watched: label === 'watched' } } },
      status: 200, statusText: 'OK', headers: {}, config,
    }
  }
  await store.updateMovieLabel(store.selectedMovies[0], 'skipped')
  assert.equal(store.selectedMovies[0].is_skipped, true)
  assert.equal(store.wishMovies.length, 0)
  await store.addToWishMovies(store.selectedMovies[0])
  assert.equal(store.selectedMovies[0].is_skipped, false)
  assert.equal(store.wishMovies.length, 1)
  await store.updateMovieLabel(store.selectedMovies[0], 'skipped')
  assert.equal(store.wishMovies.length, 0)
  await store.updateMovieLabel(store.selectedMovies[0], 'watched')
  assert.equal(store.selectedMovies[0].is_watched, true)
  assert.equal(store.selectedMovies[0].is_skipped, false)
  assert.equal(store.wishMovies.length, 0)
  await store.updateMovieLabel(store.selectedMovies[0], null)
  assert.equal(store.selectedMovies[0].is_watched, false)
  assert.equal(store.selectedMovies[0].is_skipped, false)
  assert.equal(store.selectedMovies[0].is_wished, false)
})

test('标签保存失败时恢复原标签和想看列表', async () => {
  const store = useMovieSelectionStore()
  const wished = { ...movie, is_wished: true }
  store.wishMovies = [wished]
  store.setSelectedMovies([wished])
  api.defaults.adapter = async () => { throw new Error('保存失败') }
  await assert.rejects(store.updateMovieLabel(wished, 'watched'), /保存失败/)
  assert.equal(store.selectedMovies[0].is_wished, true)
  assert.equal(store.selectedMovies[0].is_watched, false)
  assert.equal(store.selectedMovies[0].is_skipped, false)
  assert.equal(store.wishMovies.length, 1)
})
