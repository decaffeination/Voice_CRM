import http from './http'

// 本地 TTS（ChatTTS）在 CPU 上合成较慢，长文本可能耗时数分钟，
// 故带语音的请求需要显著长于默认 120s 的超时，避免 axios 提前中断。
const AUDIO_REQUEST_TIMEOUT_MS = 300000

export async function sendChat(message: string, sessionId?: string | null, withAudio = false) {
  const { data } = await http.post<{
    session_id: string
    reply: string
    audio_base64: string | null
    intent: string | null
    session_title: string | null
    citations?: Array<{
      index: number
      ref: string
      source: string
      doc_id?: string | null
      page?: number | null
      snippet?: string
      score?: number | null
    }>
  }>(
    '/chat',
    {
      message,
      session_id: sessionId,
      with_audio: withAudio,
    },
    withAudio ? { timeout: AUDIO_REQUEST_TIMEOUT_MS } : undefined,
  )
  return data
}

export async function uploadAudio(
  file: File,
  sessionId?: string | null,
  withAudio = false,
) {
  const form = new FormData()
  form.append('file', file)
  if (sessionId) form.append('session_id', sessionId)
  form.append('with_audio', withAudio ? 'true' : 'false')
  const { data } = await http.post<{
    session_id: string
    transcript: string
    reply: string
    audio_base64: string | null
    intent: string | null
    session_title: string | null
    citations?: Array<{
      index: number
      ref: string
      source: string
      doc_id?: string | null
      page?: number | null
      snippet?: string
      score?: number | null
    }>
  }>('/audio', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: withAudio ? AUDIO_REQUEST_TIMEOUT_MS : undefined,
  })
  return data
}
