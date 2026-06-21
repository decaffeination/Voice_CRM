<template>
  <div class="chat-page">
    <div class="panel">
      <div class="messages" ref="listRef">
        <div v-if="showWelcome" class="welcome">
          <h2 class="welcome-title">欢迎使用 Sales Intelligence 企业助手</h2>
          <p class="welcome-desc">统一连接知识库、CRM 与 AI 能力</p>
          <div class="quick-grid">
            <div
              v-for="card in quickCards"
              :key="card.key"
              class="quick-card"
              @click="fillQuick(card.prompt)"
            >
              <n-icon :size="22" class="quick-icon"><component :is="card.icon" /></n-icon>
              <div class="quick-label">{{ card.label }}</div>
              <div class="quick-hint">{{ card.hint }}</div>
            </div>
          </div>
        </div>
        <template v-else>
          <ChatMessageItem
            v-for="msg in messages"
            :key="msg.id"
            :message="msg"
          />
          <div v-if="historyLoading" class="loading">加载历史消息...</div>
          <div v-if="chatStore.sending" class="loading">{{ sendingHint }}</div>
        </template>
      </div>

      <div class="composer">
        <div class="toolbar">
          <n-switch
            v-model:value="withAudio"
            size="small"
            @update:value="onWithAudioChange"
          >
            <template #checked>语音回复</template>
            <template #unchecked>语音回复</template>
          </n-switch>
          <n-upload :show-file-list="false" accept="audio/*" @change="onUpload">
            <n-button size="small">上传音频</n-button>
          </n-upload>
        </div>

        <div class="input-row">
          <n-input
            v-model:value="input"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 5 }"
            placeholder="请输入问题，或使用 @ 调用业务能力（@crm @knowledge @email @customer）"
            @keydown.enter.exact.prevent="sendText"
          />
          <div class="actions">
            <n-button
              circle
              :type="recording ? 'error' : 'default'"
              :loading="wsConnecting || startingRecord"
              :disabled="chatStore.sending"
              @pointerdown.prevent="onMicPointerDown"
              @pointerup.prevent="onMicPointerUp"
              @pointercancel.prevent="onMicPointerCancel"
              @contextmenu.prevent
            >
              <template #icon><n-icon><MicOutline /></n-icon></template>
            </n-button>
            <n-button type="primary" :loading="chatStore.sending" @click="sendText">
              发送
            </n-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  NButton,
  NIcon,
  NInput,
  NSwitch,
  NUpload,
  useMessage,
  type UploadFileInfo,
} from 'naive-ui'
import {
  MicOutline,
  BookOutline,
  PeopleOutline,
  TrendingUpOutline,
  DocumentTextOutline,
  MailOutline,
} from '@vicons/ionicons5'
import ChatMessageItem from '@/components/ChatMessageItem.vue'
import { sendChat, uploadAudio } from '@/api/chat'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useSessionStore } from '@/stores/session'
import {
  AudioPlaybackManager,
  MIN_PCM_PEAK,
  MIN_PCM_RMS,
  measureInt16PcmEnergy,
} from '@/utils/audio'
import { MIN_UTTERANCE_BYTES, PCM_CHUNK_BYTES, PcmCapture } from '@/utils/pcmCapture'
import { AudioWebSocket } from '@/utils/websocket'

const route = useRoute()
const message = useMessage()
const authStore = useAuthStore()
const sessionStore = useSessionStore()
const chatStore = useChatStore()

const input = ref('')
const withAudio = ref(false)
const listRef = ref<HTMLElement | null>(null)
const wsConnected = ref(false)
const wsConnecting = ref(false)
const recording = ref(false)
const startingRecord = ref(false)

let wsClient: AudioWebSocket | null = null
let pcmCapture: PcmCapture | null = null
let recordPointerId: number | null = null
// 采集尚未就绪时用户已松手/取消：记录意图，待 start() 完成后补执行
let pendingRelease: 'stop' | 'cancel' | null = null
const ttsPlayback = new AudioPlaybackManager()
let streamingAssistantId: string | null = null
let voiceHasTts = false
const WS_SENDING_TIMEOUT_MS = 185_000
let sendingTimeoutId: ReturnType<typeof setTimeout> | null = null

const currentSessionId = computed(() => sessionStore.currentSessionId)
const messages = computed(() =>
  currentSessionId.value ? chatStore.getMessages(currentSessionId.value) : [],
)
const historyLoading = computed(() =>
  currentSessionId.value ? chatStore.isLoading(currentSessionId.value) : false,
)
const showWelcome = computed(
  () => !messages.value.length && !chatStore.sending && !historyLoading.value,
)

const sendingHint = computed(() => {
  switch (chatStore.sendingStage) {
    case 'asr':
      return '语音识别中…'
    case 'tts':
      return '正在合成语音…'
    case 'upload':
      return '正在处理上传音频…'
    case 'thinking':
    default:
      return '思考中…'
  }
})

const quickCards = [
  {
    key: 'knowledge',
    label: '知识库问答',
    hint: '@knowledge',
    icon: BookOutline,
    prompt: '@knowledge 公司的报销流程是什么？',
  },
  {
    key: 'crm',
    label: 'CRM 客户查询',
    hint: '@crm',
    icon: PeopleOutline,
    prompt: '@crm 查询客户信息',
  },
  {
    key: 'sales',
    label: '销售分析',
    hint: '数据分析',
    icon: TrendingUpOutline,
    prompt: '帮我分析本月销售漏斗与客户跟进情况',
  },
  {
    key: 'contract',
    label: '合同生成',
    hint: '@customer',
    icon: DocumentTextOutline,
    prompt: '@customer 生成标准合作合同要点',
  },
  {
    key: 'email',
    label: '邮件助手',
    hint: '@email',
    icon: MailOutline,
    prompt: '@email 帮我写一封客户跟进邮件',
  },
]

function fillQuick(prompt: string) {
  input.value = prompt
}

watch(messages, async () => {
  await nextTick()
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
})

watch(currentSessionId, async (id) => {
  if (id) {
    await chatStore.loadSessionMessages(id)
    await connectWs()
  } else {
    wsClient?.close()
    wsConnected.value = false
  }
})

watch(withAudio, (enabled) => {
  ttsPlayback.setEnabled(enabled)
})

function onWithAudioChange(enabled: boolean) {
  if (!enabled) {
    message.info('已关闭语音回复并停止播放')
  }
}

function clearSendingTimeout() {
  if (sendingTimeoutId !== null) {
    clearTimeout(sendingTimeoutId)
    sendingTimeoutId = null
  }
}

function startSendingTimeout() {
  clearSendingTimeout()
  sendingTimeoutId = setTimeout(() => {
    if (chatStore.sending) {
      chatStore.clearSending()
      streamingAssistantId = null
      message.error('语音处理超时，请重试')
    }
  }, WS_SENDING_TIMEOUT_MS)
}

function finishVoiceSending() {
  clearSendingTimeout()
  chatStore.clearSending()
}

function uid() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

async function ensureSession() {
  if (!currentSessionId.value) {
    await sessionStore.newSession()
  }
  return currentSessionId.value!
}

function applySessionTitle(sessionId: string, title?: string | null) {
  if (title) {
    sessionStore.updateSessionTitle(sessionId, title)
  }
}

async function sendText() {
  const text = input.value.trim()
  if (!text) return
  const sessionId = await ensureSession()
  chatStore.addMessage(sessionId, { id: uid(), role: 'user', content: text, channel: 'text' })
  input.value = ''
  chatStore.setSendingStage('thinking')
  const audioHint = withAudio.value
    ? message.loading('正在生成回复…', { duration: 0 })
    : null
  try {
    const res = await sendChat(text, sessionId, withAudio.value)
    sessionStore.selectSession(res.session_id)
    applySessionTitle(res.session_id, res.session_title)
    chatStore.addMessage(res.session_id, {
      id: uid(),
      role: 'assistant',
      content: res.reply,
      intent: res.intent,
      channel: 'text',
    })
    audioHint?.destroy()
    if (withAudio.value) {
      chatStore.setSendingStage('tts')
    } else {
      chatStore.clearSending()
    }
    if (res.audio_base64 && withAudio.value) {
      try {
        await ttsPlayback.playOnce(res.audio_base64)
      } catch {
        message.warning('语音播放失败（可能被浏览器自动播放策略拦截，请先与页面交互一次）')
      }
    } else if (withAudio.value) {
      message.warning('语音合成不可用，已显示文字回复')
    }
  } catch (err) {
    const isTimeout =
      (err as { code?: string })?.code === 'ECONNABORTED' ||
      /timeout/i.test((err as Error)?.message || '')
    message.error(isTimeout ? '请求超时，请重试或缩短消息' : '发送失败')
  } finally {
    audioHint?.destroy()
    chatStore.clearSending()
  }
}

async function onUpload(options: { file: UploadFileInfo }) {
  const file = options.file.file
  if (!file) return
  await processAudioFile(file, '正在处理上传音频…')
}

async function processAudioFile(file: File, hintText = '正在识别语音…') {
  const sessionId = await ensureSession()
  chatStore.setSendingStage('asr')
  const uploadHint = message.loading(hintText, { duration: 0 })
  try {
    const res = await uploadAudio(file, sessionId, withAudio.value)
    sessionStore.selectSession(res.session_id)
    applySessionTitle(res.session_id, res.session_title)
    chatStore.addMessage(res.session_id, {
      id: uid(),
      role: 'user',
      content: res.transcript,
      channel: 'voice',
      transcript: res.transcript,
    })
    chatStore.addMessage(res.session_id, {
      id: uid(),
      role: 'assistant',
      content: res.reply,
      intent: res.intent,
      channel: 'voice',
    })
    if (res.audio_base64 && withAudio.value) {
      chatStore.setSendingStage('tts')
      try {
        await ttsPlayback.playOnce(res.audio_base64)
      } catch {
        message.warning('语音播放失败')
      }
    } else if (withAudio.value) {
      message.warning('语音合成不可用，已显示文字回复')
    }
  } catch {
    message.error('音频处理失败，请重试')
  } finally {
    uploadHint.destroy()
    chatStore.clearSending()
  }
}

async function connectWs() {
  if (!currentSessionId.value || !authStore.token) return
  if (wsConnecting.value) return
  wsClient?.close()
  wsConnected.value = false
  wsClient = new AudioWebSocket()
  wsConnecting.value = true
  try {
    await wsClient.connect(
      currentSessionId.value,
      authStore.token,
      handleWsMessage,
      () => {
        wsConnected.value = false
        if (chatStore.sending) {
          finishVoiceSending()
          message.warning('语音连接已断开')
        }
      },
    )
    wsConnected.value = true
  } catch {
    message.error('语音连接失败，请重试')
  } finally {
    wsConnecting.value = false
  }
}

function handleWsMessage(msg: {
  type: string
  text?: string
  delta?: string
  data?: string
  intent?: string
  message?: string
  title?: string
  index?: number
}) {
  const sessionId = currentSessionId.value
  if (!sessionId) return

  if (msg.type === 'session_title' && msg.title) {
    applySessionTitle(sessionId, msg.title)
    return
  }

  if (msg.type === 'asr_final' && msg.text) {
    chatStore.setSendingStage('thinking')
    chatStore.addMessage(sessionId, {
      id: uid(),
      role: 'user',
      content: msg.text,
      channel: 'voice',
      transcript: msg.text,
    })
    streamingAssistantId = uid()
    chatStore.addMessage(sessionId, {
      id: streamingAssistantId,
      role: 'assistant',
      content: '',
      channel: 'voice',
    })
    ttsPlayback.clear()
  }

  if (msg.type === 'agent_text_delta' && msg.delta) {
    if (!streamingAssistantId) {
      streamingAssistantId = uid()
      chatStore.addMessage(sessionId, {
        id: streamingAssistantId,
        role: 'assistant',
        content: '',
        channel: 'voice',
      })
    }
    const current = chatStore
      .getMessages(sessionId)
      .find((m) => m.id === streamingAssistantId)
    chatStore.updateMessage(sessionId, streamingAssistantId, {
      content: `${current?.content || ''}${msg.delta}`,
    })
  }

  if (msg.type === 'agent_text' && msg.text) {
    chatStore.clearSending()
    if (streamingAssistantId) {
      chatStore.updateMessage(sessionId, streamingAssistantId, {
        content: msg.text,
        intent: msg.intent,
      })
    } else {
      chatStore.addMessage(sessionId, {
        id: uid(),
        role: 'assistant',
        content: msg.text,
        intent: msg.intent,
        channel: 'voice',
      })
    }
    streamingAssistantId = null
  }

  if (msg.type === 'tts_audio_chunk' && msg.data && withAudio.value) {
    voiceHasTts = true
    chatStore.setSendingStage('tts')
    ttsPlayback.enqueue(msg.data)
  }

  if (msg.type === 'tts_audio' && msg.data && withAudio.value) {
    void ttsPlayback.playOnce(msg.data)
  }

  if (msg.type === 'tts_done') {
    clearSendingTimeout()
    chatStore.clearSending()
    if (withAudio.value && !voiceHasTts) {
      message.warning('语音合成不可用，已显示文字回复')
    }
  }

  if (msg.type === 'error') {
    finishVoiceSending()
    streamingAssistantId = null
    message.error(msg.message || '语音处理失败')
  }
}

async function startRecord() {
  if (recording.value || startingRecord.value || pcmCapture || chatStore.sending) return
  startingRecord.value = true
  pendingRelease = null
  try {
    await ensureSession()
    if (!wsConnected.value) {
      await connectWs()
      if (!wsConnected.value) return
    }
    if (!wsClient) return
    wsClient.send({ type: 'reset' })
    pcmCapture = new PcmCapture()
    await pcmCapture.start()
  } catch {
    pcmCapture?.destroy()
    pcmCapture = null
    startingRecord.value = false
    pendingRelease = null
    message.error('无法访问麦克风，请检查浏览器麦克风权限')
    return
  }
  startingRecord.value = false
  recording.value = true

  const pending = pendingRelease
  pendingRelease = null
  if (pending === 'cancel') {
    releaseRecording()
    wsClient?.send({ type: 'reset' })
  } else if (pending === 'stop') {
    await stopRecord()
  }
}

function releaseRecording() {
  recordPointerId = null
  if (!recording.value && !pcmCapture) return
  recording.value = false
  pcmCapture?.destroy()
  pcmCapture = null
}

function onMicPointerDown(event: PointerEvent) {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  if (recordPointerId !== null) return
  recordPointerId = event.pointerId
  const target = event.currentTarget as HTMLElement | null
  target?.setPointerCapture(event.pointerId)
  void startRecord()
}

function onMicPointerUp(event: PointerEvent) {
  if (recordPointerId !== event.pointerId) return
  recordPointerId = null
  const target = event.currentTarget as HTMLElement | null
  try {
    target?.releasePointerCapture(event.pointerId)
  } catch {
    // 捕获可能已被浏览器释放
  }
  if (startingRecord.value) {
    pendingRelease = 'stop'
    return
  }
  void stopRecord()
}

function onMicPointerCancel(event: PointerEvent) {
  if (recordPointerId !== event.pointerId) return
  recordPointerId = null
  if (startingRecord.value) {
    pendingRelease = 'cancel'
    return
  }
  if (recording.value) {
    releaseRecording()
    wsClient?.send({ type: 'reset' })
  }
}

async function stopRecord() {
  if (!recording.value || !wsClient || !pcmCapture) return
  recording.value = false
  let pcm: Uint8Array
  try {
    pcm = await pcmCapture.stopAndEncode()
  } catch {
    pcmCapture?.destroy()
    pcmCapture = null
    message.error('音频处理失败，请重试')
    return
  }
  pcmCapture = null

  if (pcm.length < MIN_UTTERANCE_BYTES) {
    message.warning('录音太短，请按住说话至少 0.5 秒')
    wsClient.send({ type: 'reset' })
    return
  }

  const energy = measureInt16PcmEnergy(pcm)
  if (energy.rms < MIN_PCM_RMS && energy.maxAbs < MIN_PCM_PEAK) {
    message.warning('未检测到有效语音，请靠近麦克风或检查浏览器麦克风权限')
    wsClient.send({ type: 'reset' })
    return
  }

  for (let offset = 0; offset < pcm.length; offset += PCM_CHUNK_BYTES) {
    wsClient.sendPcm(pcm.subarray(offset, offset + PCM_CHUNK_BYTES))
  }

  voiceHasTts = false
  chatStore.setSendingStage('asr')
  startSendingTimeout()
  wsClient.end(withAudio.value)
}

onMounted(async () => {
  ttsPlayback.setEnabled(withAudio.value)
  const q = route.query.q
  if (typeof q === 'string' && q) input.value = q
  if (currentSessionId.value) {
    await chatStore.loadSessionMessages(currentSessionId.value)
    await connectWs()
  }
})

onUnmounted(() => {
  clearSendingTimeout()
  ttsPlayback.stop()
  wsClient?.close()
  releaseRecording()
})
</script>

<style scoped>
.chat-page {
  height: calc(100vh - 57px);
  padding: 24px;
  box-sizing: border-box;
}
.panel {
  height: 100%;
  width: 100%;
  background: #fff;
  border: 1px solid #ececec;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
}
.messages {
  flex: 1;
  overflow: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
}
.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px 16px 40px;
  text-align: center;
}
.welcome-title {
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  color: #111;
}
.welcome-desc {
  margin: 10px 0 32px;
  font-size: 14px;
  color: #888;
}
.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  width: 100%;
  max-width: 720px;
}
.quick-card {
  background: #fafafa;
  border: 1px solid #ececec;
  border-radius: 12px;
  padding: 18px 14px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  text-align: left;
}
.quick-card:hover {
  border-color: #ccc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  background: #fff;
}
.quick-icon {
  color: #333;
  margin-bottom: 8px;
}
.quick-label {
  font-size: 14px;
  font-weight: 600;
  color: #222;
}
.quick-hint {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
@media (max-width: 768px) {
  .quick-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
.loading {
  color: #888;
  font-size: 13px;
  padding: 8px 0;
}
.composer {
  border-top: 1px solid #ececec;
  padding: 16px;
}
.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: flex-start;
  margin-bottom: 12px;
}
.input-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
