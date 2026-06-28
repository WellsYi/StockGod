import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

// ── 信号 ──

export function listSignals(params) {
  return http.get('/signals', { params }).then(r => r.data)
}

export function getSignal(id) {
  return http.get(`/signals/${id}`).then(r => r.data)
}

export function countSignalsToday() {
  return http.get('/signals/today').then(r => r.data)
}

// ── 准确率 ──

export function listAccuracy(params) {
  return http.get('/accuracy', { params }).then(r => r.data)
}

export function updateAccuracy(signalId, body) {
  return http.patch(`/accuracy/${signalId}`, body).then(r => r.data)
}

// ── B站 ──

export function listBili(params) {
  return http.get('/bili', { params }).then(r => r.data)
}

export function getBili(dynamicId) {
  return http.get(`/bili/${dynamicId}`).then(r => r.data)
}

// ── 涨停 ──

export function listLimitUp(params) {
  return http.get('/limit-up', { params }).then(r => r.data)
}

// ── 监控 ──

export function getMonitorStatus() {
  return http.get('/monitor').then(r => r.data)
}

export function startMonitor(name) {
  return http.post(`/monitor/${name}/start`).then(r => r.data)
}

export function stopMonitor(name) {
  return http.post(`/monitor/${name}/stop`).then(r => r.data)
}

// ── 股票池 ──

export function listStocks() {
  return http.get('/stocks').then(r => r.data)
}

export function addStock(code) {
  return http.post('/stocks', { code }).then(r => r.data)
}

export function removeStock(code) {
  return http.delete(`/stocks/${code}`).then(r => r.data)
}

// ── 健康 ──

export function getHealth() {
  return http.get('/health').then(r => r.data)
}
