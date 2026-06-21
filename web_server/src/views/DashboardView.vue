<template>
  <div class="page">
    <n-spin :show="loading">
      <section class="section">
        <div class="section-head">
          <h3>系统概览</h3>
          <n-tag :type="systemStatusType" size="small" round>
            {{ data?.overview.system_status ?? '-' }}
          </n-tag>
        </div>
        <n-grid :cols="7" :x-gap="12" :y-gap="12" responsive="screen" item-responsive>
          <n-gi span="7 m:4 l:1">
            <div class="stat-card">
              <div class="stat-label">今日会话数</div>
              <div class="stat-value">{{ data?.overview.today_sessions ?? 0 }}</div>
            </div>
          </n-gi>
          <n-gi span="7 m:3 l:1">
            <div class="stat-card">
              <div class="stat-label">总会话数</div>
              <div class="stat-value">{{ data?.overview.total_sessions ?? 0 }}</div>
            </div>
          </n-gi>
          <n-gi span="7 m:4 l:1">
            <div class="stat-card">
              <div class="stat-label">知识库文档数</div>
              <div class="stat-value">{{ data?.overview.knowledge_documents ?? 0 }}</div>
            </div>
          </n-gi>
          <n-gi span="7 m:3 l:1">
            <div class="stat-card">
              <div class="stat-label">客户数量</div>
              <div class="stat-value">{{ data?.overview.customer_count ?? 0 }}</div>
            </div>
          </n-gi>
          <n-gi span="7 m:4 l:1">
            <div class="stat-card">
              <div class="stat-label">AI 回答次数</div>
              <div class="stat-value">{{ data?.overview.ai_answer_count ?? 0 }}</div>
            </div>
          </n-gi>
          <n-gi span="7 m:3 l:1">
            <div class="stat-card">
              <div class="stat-label">当前在线用户</div>
              <div class="stat-value">{{ data?.overview.online_users ?? 0 }}</div>
            </div>
          </n-gi>
          <n-gi span="7 m:4 l:1">
            <div class="stat-card">
              <div class="stat-label">系统状态</div>
              <div class="stat-value small">{{ data?.overview.system_status ?? '-' }}</div>
            </div>
          </n-gi>
        </n-grid>
      </section>

      <section class="section">
        <div class="section-head"><h3>AI 助手运行情况</h3></div>
        <n-grid :cols="5" :x-gap="12" :y-gap="12" responsive="screen" item-responsive>
          <n-gi span="5 m:3 l:1">
            <div class="stat-card">
              <div class="stat-label">今日问答次数</div>
              <div class="stat-value">{{ data?.ai_runtime.today_qa_count ?? 0 }}</div>
            </div>
          </n-gi>
          <n-gi span="5 m:2 l:1">
            <div class="stat-card">
              <div class="stat-label">知识库命中率</div>
              <div class="stat-value small">
                {{ formatRate(data?.ai_runtime.knowledge_hit_rate) }}
              </div>
            </div>
          </n-gi>
          <n-gi span="5 m:3 l:1">
            <div class="stat-card">
              <div class="stat-label">未命中问题数</div>
              <div class="stat-value">{{ data?.ai_runtime.knowledge_miss_count ?? 0 }}</div>
            </div>
          </n-gi>
          <n-gi span="5 m:2 l:1">
            <div class="stat-card">
              <div class="stat-label">平均响应时间</div>
              <div class="stat-value small">{{ formatMs(data?.ai_runtime.avg_response_time_ms) }}</div>
            </div>
          </n-gi>
          <n-gi span="5 m:5 l:1">
            <div class="stat-card">
              <div class="stat-label">Token 消耗</div>
              <div class="stat-value small">{{ formatToken(data?.ai_runtime.token_consumption) }}</div>
            </div>
          </n-gi>
        </n-grid>
      </section>

      <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
        <n-gi span="2 l:1">
          <section class="panel">
            <div class="section-head">
              <h3>知识库概览</h3>
              <n-space size="small">
                <n-button size="small" @click="router.push('/knowledge')">进入知识库</n-button>
                <n-button v-if="isAdmin" size="small" @click="router.push('/knowledge')">上传文档</n-button>
                <n-button size="small" @click="router.push('/knowledge')">检索测试</n-button>
              </n-space>
            </div>
            <div class="mini-stats">
              <div><span>文档总数</span><b>{{ data?.knowledge.document_count ?? 0 }}</b></div>
              <div><span>Chunk 总数</span><b>{{ data?.knowledge.chunk_count ?? 0 }}</b></div>
              <div><span>最近更新</span><b>{{ formatTime(data?.knowledge.last_updated) }}</b></div>
              <div><span>状态</span><b>{{ data?.knowledge.kb_status ?? '-' }}</b></div>
            </div>
            <div class="sub-block">
              <h4>最近上传文档</h4>
              <div v-for="doc in data?.knowledge.recent_documents ?? []" :key="doc.doc_id" class="list-row">
                <span class="name">{{ doc.filename }}</span>
                <span class="meta">{{ doc.chunk_count }} chunks</span>
              </div>
              <n-empty v-if="!data?.knowledge.recent_documents?.length" size="small" description="暂无文档" />
            </div>
            <div class="sub-block">
              <h4>热门知识文档</h4>
              <div v-for="doc in data?.knowledge.popular_documents ?? []" :key="doc.doc_id" class="list-row">
                <span class="name">{{ doc.filename }}</span>
                <span class="meta">{{ doc.chunk_count }} chunks</span>
              </div>
              <n-empty v-if="!data?.knowledge.popular_documents?.length" size="small" description="暂无数据" />
            </div>
          </section>
        </n-gi>

        <n-gi span="2 l:1">
          <section class="panel">
            <div class="section-head">
              <h3>CRM 概览</h3>
              <n-space size="small">
                <n-button size="small" @click="router.push('/chat')">客户管理</n-button>
                <n-button size="small" @click="router.push('/chat')">新建客户</n-button>
              </n-space>
            </div>
            <div class="mini-stats">
              <div><span>客户总数</span><b>{{ data?.crm.customer_count ?? 0 }}</b></div>
              <div><span>本周新增</span><b>{{ data?.crm.new_customers_week ?? 0 }}</b></div>
              <div><span>待跟进客户</span><b>{{ data?.crm.pending_followups ?? 0 }}</b></div>
            </div>
            <div class="sub-block">
              <h4>最近跟进记录</h4>
              <div
                v-for="item in data?.crm.recent_followups ?? []"
                :key="item.id"
                class="list-row column"
              >
                <div class="row-top">
                  <span class="name">{{ item.customer_name }}</span>
                  <span class="meta">{{ formatTime(item.created_at) }}</span>
                </div>
                <div class="desc">{{ item.content }}</div>
              </div>
              <n-empty v-if="!data?.crm.recent_followups?.length" size="small" description="暂无跟进" />
            </div>
          </section>
        </n-gi>
      </n-grid>

      <n-grid :cols="2" :x-gap="16" :y-gap="16" class="bottom-grid" responsive="screen" item-responsive>
        <n-gi span="2 l:1">
          <section class="panel">
            <div class="section-head">
              <h3>最近活动</h3>
              <n-button v-if="isAdmin" text size="small" @click="router.push('/admin/audit')">
                查看全部
              </n-button>
            </div>
            <div class="activity-list">
              <div v-for="(item, idx) in data?.recent_activities ?? []" :key="idx" class="activity-item">
                <div class="activity-dot" />
                <div class="activity-body">
                  <div class="activity-top">
                    <n-tag size="tiny" :bordered="false">{{ item.label }}</n-tag>
                    <span class="activity-time">{{ formatTime(item.created_at) }}</span>
                  </div>
                  <div class="activity-desc">{{ item.description }}</div>
                  <div class="activity-user">{{ item.user_name }}</div>
                </div>
              </div>
              <n-empty v-if="!data?.recent_activities?.length" size="small" description="暂无活动" />
            </div>
          </section>
        </n-gi>

        <n-gi span="2 l:1">
          <section class="panel">
            <div class="section-head"><h3>系统状态</h3></div>
            <div class="service-grid">
              <div
                v-for="svc in data?.system_status ?? []"
                :key="svc.key"
                class="service-item"
              >
                <span class="service-name">{{ svc.name }}</span>
                <n-tag :type="statusTagType(svc.status)" size="small" round>{{ svc.status }}</n-tag>
              </div>
            </div>
          </section>
        </n-gi>
      </n-grid>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NEmpty, NGi, NGrid, NSpace, NSpin, NTag, useMessage } from 'naive-ui'
import { fetchDashboardOverview, type DashboardOverview } from '@/api/dashboard'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const loading = ref(false)
const data = ref<DashboardOverview | null>(null)

const isAdmin = computed(() => authStore.user?.roles?.includes('Admin') ?? false)

const systemStatusType = computed(() => {
  const s = data.value?.overview.system_status
  if (s === '正常') return 'success'
  if (s === '降级') return 'warning'
  if (s === '异常') return 'error'
  return 'default'
})

function formatTime(value: string | null | undefined) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

function formatRate(value: number | null | undefined) {
  if (value == null) return '—'
  return `${value}%`
}

function formatMs(value: number | null | undefined) {
  if (value == null) return '—'
  return `${value} ms`
}

function formatToken(value: number | null | undefined) {
  if (value == null) return '暂无统计'
  return String(value)
}

function statusTagType(status: string) {
  if (status === '正常') return 'success'
  if (status === '未启用' || status === '未配置') return 'default'
  if (status === '降级') return 'warning'
  return 'error'
}

async function loadData() {
  loading.value = true
  try {
    data.value = await fetchDashboardOverview()
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : '加载概览失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page {
  padding: 24px;
  box-sizing: border-box;
}
.section {
  margin-bottom: 20px;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}
.section-head h3,
.panel h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.stat-card,
.panel {
  background: #fff;
  border: 1px solid #ececec;
  border-radius: 14px;
  padding: 16px;
}
.stat-label {
  font-size: 13px;
  color: #888;
}
.stat-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 600;
  color: #111;
}
.stat-value.small {
  font-size: 20px;
}
.panel {
  height: 100%;
}
.mini-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}
.mini-stats div {
  background: #fafafa;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mini-stats span {
  font-size: 12px;
  color: #888;
}
.mini-stats b {
  font-size: 18px;
  font-weight: 600;
}
.sub-block {
  margin-top: 14px;
}
.sub-block h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #666;
  font-weight: 500;
}
.list-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f3f3f3;
  gap: 8px;
}
.list-row.column {
  flex-direction: column;
  align-items: stretch;
}
.row-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.name {
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  font-size: 12px;
  color: #999;
  flex-shrink: 0;
}
.desc {
  font-size: 12px;
  color: #666;
  line-height: 1.5;
}
.bottom-grid {
  margin-top: 16px;
}
.activity-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.activity-item {
  display: flex;
  gap: 10px;
}
.activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #111;
  margin-top: 6px;
  flex-shrink: 0;
}
.activity-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.activity-time {
  font-size: 12px;
  color: #999;
}
.activity-desc {
  font-size: 13px;
  color: #444;
  margin-top: 4px;
  line-height: 1.5;
}
.activity-user {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.service-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.service-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 8px;
}
.service-name {
  font-size: 13px;
  color: #333;
}
</style>
