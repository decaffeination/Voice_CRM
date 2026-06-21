/**
 * AudioWorklet：在音频渲染线程采集 PCM，避免 ScriptProcessor + 扬声器路由触发 AEC 静音。
 */
class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0]
    if (channel && channel.length > 0) {
      this.port.postMessage(new Float32Array(channel))
    }
    return true
  }
}

registerProcessor('pcm-capture-processor', PcmCaptureProcessor)
