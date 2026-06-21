function detectAudioMime(base64: string): string {
  try {
    const head = atob(base64.slice(0, 24))
    const bytes = new Uint8Array(head.length)
    for (let i = 0; i < head.length; i += 1) {
      bytes[i] = head.charCodeAt(i)
    }
    if (bytes[0] === 0x1a && bytes[1] === 0x45 && bytes[2] === 0xdf && bytes[3] === 0xa3) {
      return 'audio/webm'
    }
    if (head.startsWith('RIFF')) {
      return 'audio/wav'
    }
    if (head.startsWith('ID3') || (bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0)) {
      return 'audio/mpeg'
    }
  } catch {
    // 解码失败时回退默认 mp3
  }
  return 'audio/mpeg'
}

function floatSampleToInt16(s: number): number {
  const clamped = Math.max(-1, Math.min(1, s))
  return clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
}

/** 16kHz int16 PCM 最低 RMS，低于此（且峰值也低）视为近静音 */
export const MIN_PCM_RMS = 60
/** 16kHz int16 PCM 最低峰值；存在明显峰值时即视为有效语音 */
export const MIN_PCM_PEAK = 800

export function measureInt16PcmEnergy(pcm: Uint8Array): { rms: number; maxAbs: number } {
  const sampleCount = pcm.byteLength / 2
  if (sampleCount <= 0) {
    return { rms: 0, maxAbs: 0 }
  }
  const samples = new Int16Array(pcm.buffer, pcm.byteOffset, sampleCount)
  let sumSq = 0
  let maxAbs = 0
  for (let i = 0; i < samples.length; i += 1) {
    const value = samples[i]
    const abs = Math.abs(value)
    if (abs > maxAbs) maxAbs = abs
    sumSq += value * value
  }
  return {
    rms: Math.sqrt(sumSq / samples.length),
    maxAbs,
  }
}

/** 将 Float32 PCM 线性插值重采样并转为 16kHz int16 bytes */
export function floatTo16kPcm(input: Float32Array, inputSampleRate: number) {
  const targetRate = 16000
  if (input.length === 0) return new Uint8Array(0)

  if (inputSampleRate === targetRate) {
    const direct = new Int16Array(input.length)
    for (let i = 0; i < input.length; i += 1) {
      direct[i] = floatSampleToInt16(input[i])
    }
    return new Uint8Array(direct.buffer)
  }

  const newLength = Math.max(1, Math.round((input.length * targetRate) / inputSampleRate))
  const result = new Int16Array(newLength)
  for (let i = 0; i < newLength; i += 1) {
    const srcIdx = (i * inputSampleRate) / targetRate
    const idx0 = Math.floor(srcIdx)
    const idx1 = Math.min(idx0 + 1, input.length - 1)
    const frac = srcIdx - idx0
    const s = input[idx0] * (1 - frac) + input[idx1] * frac
    result[i] = floatSampleToInt16(s)
  }
  return new Uint8Array(result.buffer)
}

/** 使用 OfflineAudioContext 做高质量重采样（推荐用于整段录音）。 */
export async function resampleTo16kPcm(
  input: Float32Array,
  inputSampleRate: number,
): Promise<Uint8Array> {
  if (!input.length) return new Uint8Array(0)
  if (inputSampleRate === 16000) {
    return floatTo16kPcm(input, 16000)
  }

  const durationSec = input.length / inputSampleRate
  const outputLength = Math.max(1, Math.ceil(durationSec * 16000))
  const offline = new OfflineAudioContext(1, outputLength, 16000)
  const buffer = offline.createBuffer(1, input.length, inputSampleRate)
  buffer.copyToChannel(input, 0)
  const source = offline.createBufferSource()
  source.buffer = buffer
  source.connect(offline.destination)
  source.start(0)
  const rendered = await offline.startRendering()
  return floatTo16kPcm(rendered.getChannelData(0), 16000)
}

function createAudioElement(base64: string, mime?: string): HTMLAudioElement {
  const resolvedMime = mime || detectAudioMime(base64)
  const audio = new Audio(`data:${resolvedMime};base64,${base64}`)
  return audio
}

export function playBase64Audio(base64: string, mime?: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const audio = createAudioElement(base64, mime)
    audio.addEventListener('ended', () => resolve(), { once: true })
    audio.addEventListener(
      'error',
      () => reject(new Error('audio playback error')),
      { once: true },
    )
    void audio.play().catch(reject)
  })
}

/**
 * 统一语音播放：受「语音回复」开关控制，支持停止/暂停。
 * 关闭开关会立即停止当前播放并丢弃队列。
 */
export class AudioPlaybackManager {
  private queue: string[] = []
  private playing = false
  private enabled = true
  private paused = false
  private current: HTMLAudioElement | null = null

  setEnabled(enabled: boolean) {
    this.enabled = enabled
    if (!enabled) {
      this.stop()
    } else {
      this.paused = false
    }
  }

  isEnabled() {
    return this.enabled
  }

  pause() {
    if (!this.enabled) return
    this.paused = true
    this.current?.pause()
  }

  resume() {
    if (!this.enabled) return
    this.paused = false
    if (this.current) {
      void this.current.play().catch(() => {})
    } else {
      void this.playNext()
    }
  }

  stop() {
    this.queue = []
    this.playing = false
    this.paused = false
    if (this.current) {
      this.current.pause()
      this.current.src = ''
      this.current = null
    }
  }

  clear() {
    this.stop()
  }

  enqueue(base64: string) {
    if (!this.enabled) return
    this.queue.push(base64)
    void this.playNext()
  }

  playOnce(base64: string, mime?: string): Promise<void> {
    if (!this.enabled) return Promise.resolve()
    this.stop()
    return new Promise((resolve, reject) => {
      const audio = createAudioElement(base64, mime)
      this.current = audio
      this.playing = true
      audio.addEventListener(
        'ended',
        () => {
          this.playing = false
          if (this.current === audio) this.current = null
          resolve()
        },
        { once: true },
      )
      audio.addEventListener(
        'error',
        () => {
          this.playing = false
          if (this.current === audio) this.current = null
          reject(new Error('audio playback error'))
        },
        { once: true },
      )
      void audio.play().catch(reject)
    })
  }

  private async playNext() {
    if (this.playing || this.paused || !this.enabled || this.queue.length === 0) {
      return
    }
    this.playing = true
    const base64 = this.queue.shift()
    if (!base64) {
      this.playing = false
      return
    }
    const audio = createAudioElement(base64)
    this.current = audio
    try {
      await new Promise<void>((resolve, reject) => {
        audio.addEventListener('ended', () => resolve(), { once: true })
        audio.addEventListener('error', () => reject(new Error('audio playback error')), {
          once: true,
        })
        void audio.play().catch(reject)
      })
    } catch {
      // 浏览器自动播放策略等导致失败时跳过该分片
    } finally {
      if (this.current === audio) this.current = null
      this.playing = false
      void this.playNext()
    }
  }
}

/** @deprecated 使用 AudioPlaybackManager */
export class AudioPlaybackQueue extends AudioPlaybackManager {}

export function base64ToBlob(base64: string, mime: string) {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return new Blob([bytes], { type: mime })
}

export function bytesToBase64(bytes: Uint8Array) {
  let binary = ''
  const chunk = 0x8000
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk))
  }
  return btoa(binary)
}
