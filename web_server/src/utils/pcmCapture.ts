import { resampleTo16kPcm } from '@/utils/audio'

/** 静态 worklet（public/），避免 Vite 打包成错误 MIME 的 data URL */
const PCM_CAPTURE_WORKLET_URL = `${import.meta.env.BASE_URL}pcm-capture.worklet.js`

/** 16kHz mono int16，与后端 WS 协议一致 */
export const PCM_CHUNK_BYTES = 3200
/** 约 0.5 秒有效语音（16kHz * 2 bytes） */
export const MIN_UTTERANCE_BYTES = 8000

const AUDIO_CONSTRAINTS: MediaTrackConstraints = {
  channelCount: 1,
  echoCancellation: false,
  noiseSuppression: false,
  autoGainControl: false,
}

/**
 * 麦克风采集：录音期间缓存 Float32，松手后重采样为 16k PCM。
 * 优先 AudioWorklet；不支持时回退 ScriptProcessor。
 */
export class PcmCapture {
  private audioContext: AudioContext | null = null
  private mediaStream: MediaStream | null = null
  private worklet: AudioWorkletNode | null = null
  private processor: ScriptProcessorNode | null = null
  private silentGain: GainNode | null = null
  private onWorkletMessage: ((event: MessageEvent<Float32Array>) => void) | null = null
  private chunks: Float32Array[] = []
  private totalSamples = 0
  private sampleRate = 48000

  async start(): Promise<void> {
    this.chunks = []
    this.totalSamples = 0

    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: AUDIO_CONSTRAINTS,
    })
    await this.applyTrackConstraints()

    this.audioContext = new AudioContext()
    await this.audioContext.resume()
    this.sampleRate = this.audioContext.sampleRate

    const source = this.audioContext.createMediaStreamSource(this.mediaStream)
    this.silentGain = this.audioContext.createGain()
    this.silentGain.gain.value = 0

    const workletReady = await this.tryStartWorklet(source)
    if (!workletReady) {
      this.startScriptProcessor(source)
    }

    // 图必须接到 destination 才会跑，gain=0 避免外放触发浏览器 AEC
    this.silentGain.connect(this.audioContext.destination)
  }

  private async applyTrackConstraints(): Promise<void> {
    const track = this.mediaStream?.getAudioTracks()[0]
    if (!track) return
    try {
      await track.applyConstraints(AUDIO_CONSTRAINTS)
    } catch {
      // 部分浏览器/设备不支持逐项约束，忽略
    }
  }

  private appendChunk(input: Float32Array): void {
    if (!input.length) return
    this.chunks.push(new Float32Array(input))
    this.totalSamples += input.length
  }

  private async tryStartWorklet(source: MediaStreamAudioSourceNode): Promise<boolean> {
    if (!this.audioContext || !this.silentGain) return false
    try {
      await this.audioContext.audioWorklet.addModule(PCM_CAPTURE_WORKLET_URL)
      this.worklet = new AudioWorkletNode(this.audioContext, 'pcm-capture-processor')
      this.onWorkletMessage = (event: MessageEvent<Float32Array>) => {
        this.appendChunk(event.data)
      }
      this.worklet.port.onmessage = this.onWorkletMessage
      source.connect(this.worklet)
      this.worklet.connect(this.silentGain)
      return true
    } catch {
      this.worklet?.disconnect()
      this.worklet = null
      this.onWorkletMessage = null
      return false
    }
  }

  private startScriptProcessor(source: MediaStreamAudioSourceNode): void {
    if (!this.audioContext || !this.silentGain) return
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1)
    this.processor.onaudioprocess = (event) => {
      this.appendChunk(event.inputBuffer.getChannelData(0))
    }
    source.connect(this.processor)
    this.processor.connect(this.silentGain)
  }

  /** 停止采集并重采样；返回 16kHz mono int16 PCM。 */
  async stopAndEncode(): Promise<Uint8Array> {
    const merged = new Float32Array(this.totalSamples)
    let offset = 0
    for (const chunk of this.chunks) {
      merged.set(chunk, offset)
      offset += chunk.length
    }
    const sampleRate = this.sampleRate
    this.destroy()
    if (!merged.length) return new Uint8Array(0)
    return resampleTo16kPcm(merged, sampleRate)
  }

  destroy(): void {
    if (this.worklet) {
      if (this.onWorkletMessage) {
        this.worklet.port.onmessage = null
      }
      this.worklet.disconnect()
      this.worklet = null
      this.onWorkletMessage = null
    }
    this.processor?.disconnect()
    this.processor = null
    this.silentGain?.disconnect()
    this.silentGain = null
    this.mediaStream?.getTracks().forEach((track) => track.stop())
    this.mediaStream = null
    if (this.audioContext) {
      void this.audioContext.close()
      this.audioContext = null
    }
    this.chunks = []
    this.totalSamples = 0
  }
}
