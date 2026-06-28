import { ref, onMounted, onUnmounted } from 'vue'

export function useWebSocket() {
  const connected = ref(false)
  const lastMessage = ref(null)
  let ws = null
  let pingTimer = null
  const handlers = new Set()

  function onMessage(fn) {
    handlers.add(fn)
    return () => handlers.delete(fn)
  }

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${proto}//${location.host}/ws`)

    ws.onopen = () => { connected.value = true }
    ws.onclose = () => { connected.value = false }
    ws.onmessage = (e) => {
      lastMessage.value = e.data
      handlers.forEach(fn => fn(e.data))
    }
    ws.onerror = () => { connected.value = false }
  }

  function disconnect() {
    clearInterval(pingTimer)
    if (ws) { ws.close(); ws = null }
    connected.value = false
  }

  onMounted(() => {
    connect()
    pingTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping')
    }, 30000)
  })

  onUnmounted(disconnect)

  return { connected, lastMessage, onMessage, connect, disconnect }
}
