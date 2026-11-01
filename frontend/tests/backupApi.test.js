import assert from 'node:assert/strict'
import { createServer as createHttpServer } from 'node:http'
import { after, before, test } from 'node:test'
import { createServer } from 'vite'

let server
let api
let exportBackendData
let importBackendData

before(async () => {
  server = await createServer({
    server: { middlewareMode: true, hmr: { server: createHttpServer() } },
    appType: 'custom',
  })
  ;({ default: api, exportBackendData, importBackendData } = await server.ssrLoadModule('/src/api/index.js'))
})

after(async () => server?.close())

test('导出只读取后端备份接口', async () => {
  api.defaults.adapter = async (config) => {
    assert.equal(config.baseURL, '/api')
    assert.equal(config.url, '/backups/export')
    assert.equal(config.method, 'get')
    return { data: { success: true, data: {} }, status: 200, statusText: 'OK', headers: {}, config }
  }
  assert.equal((await exportBackendData()).data.success, true)
})

test('导入发送原始备份及显式覆盖确认，保留服务端错误', async () => {
  const backup = { success: true, data: { movies: [{ id: -123 }] } }
  api.defaults.adapter = async (config) => {
    assert.equal(config.url, '/backups/import')
    assert.equal(config.method, 'post')
    assert.deepEqual(JSON.parse(config.data), { backup, confirm_replace: true })
    return { data: { success: true, data: { movies: 1 } }, status: 200, statusText: 'OK', headers: {}, config }
  }
  assert.equal((await importBackendData(backup)).data.data.movies, 1)
  api.defaults.adapter = async () => { throw new Error('导入失败') }
  await assert.rejects(importBackendData(backup), /导入失败/)
})
