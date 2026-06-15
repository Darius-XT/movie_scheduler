// Read a fetch Response whose body is text/event-stream and invoke onData
// with each parsed JSON payload (server frames each event as `data: <json>\n\n`).
export const readSseStream = async (response, onData) => {
  if (!response.body) throw new Error('未收到更新响应流')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = JSON.parse(line.substring(6))
      onData(data)
    }
  }
}
