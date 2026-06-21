import type { WsMessage } from '@/types'
import { bytesToBase64 } from '@/utils/audio'

export type WsHandler = (msg: WsMessage) => void
export type WsCloseHandler = () => void

export class AudioWebSocket {
  private ws: WebSocket | null = null

  connect(
    sessionId: string,
    token: string,
    onMessage: WsHandler,
    onClose?: WsCloseHandler,
  ) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/audio/${sessionId}?token=${encodeURIComponent(token)}`
    this.ws = new WebSocket(url)
    this.ws.onmessage = (event) => {
      onMessage(JSON.parse(event.data))
    }
    this.ws.onclose = () => {
      onClose?.()
    }
    return new Promise<void>((resolve, reject) => {
      if (!this.ws) return reject()
      this.ws.onopen = () => resolve()
      this.ws.onerror = () => reject(new Error('WebSocket 连接失败'))
    })
  }

  send(data: WsMessage) {
    this.ws?.send(JSON.stringify(data))
  }

  sendPcm(pcmBytes: Uint8Array) {
    this.send({ type: 'audio', data: bytesToBase64(pcmBytes) })
  }

  end(withTts = true) {
    this.send({ type: 'end', with_tts: withTts })
  }

  ping() {
    this.send({ type: 'ping' })
  }

  close() {
    this.ws?.close()
    this.ws = null
  }
}
