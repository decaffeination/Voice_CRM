<template>
  <div class="kb-page">
    <div class="kb-container">
      <div class="page-header">
        <div>
          <h2>知识库</h2>
          <p class="subtitle">管理企业文档，供 AI 检索与问答引用</p>
        </div>
      </div>

      <n-grid :cols="4" :x-gap="16" :y-gap="16" class="stat-grid">
        <n-gi>
          <n-card size="small" :bordered="true" class="stat-card">
            <n-statistic label="文档数" :value="stats?.document_count ?? 0" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" :bordered="true" class="stat-card">
            <n-statistic label="知识片段数" :value="stats?.chunk_count ?? 0" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" :bordered="true" class="stat-card">
            <n-statistic label="最近更新时间" :value="lastUpdatedLabel" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" :bordered="true" class="stat-card">
            <div class="status-stat">
              <span class="stat-label">知识库状态</span>
              <n-tag :type="kbStatusType" size="small" round>{{ stats?.kb_status ?? '-' }}</n-tag>
            </div>
          </n-card>
        </n-gi>
      </n-grid>

      <n-card size="small" class="table-card">
        <div class="toolbar">
          <n-input
            v-model:value="searchKeyword"
            placeholder="搜索文件名、分类..."
            clearable
            class="search-input"
          >
            <template #prefix>
              <n-icon><SearchOutline /></n-icon>
            </template>
          </n-input>
          <div v-if="isAdmin" class="toolbar-actions">
            <n-upload
              :show-file-list="false"
              :custom-request="handleUpload"
              accept=".txt,.pdf,.docx"
            >
              <n-button type="primary" :loading="uploading">上传文档</n-button>
            </n-upload>
            <n-button :loading="ingesting" @click="handleIngestDirectory">扫描目录导入</n-button>
            <n-button :loading="rebuilding" @click="handleRebuild">重建索引</n-button>
          </div>
        </div>

        <n-spin :show="loading">
          <n-data-table
            :columns="columns"
            :data="filteredDocuments"
            :bordered="false"
            size="small"
            :pagination="{ pageSize: 10 }"
            :scroll-x="1100"
          />
        </n-spin>
      </n-card>

      <n-card size="small" title="检索测试" class="search-test-card">
        <div class="search-test-form">
          <n-input
            v-model:value="testQuery"
            placeholder="输入测试问题，例如：报销流程是什么"
            clearable
            @keydown.enter="handleSearchTest"
          />
          <div class="search-test-controls">
            <span class="topk-label">TopK</span>
            <n-input-number v-model:value="testTopK" :min="1" :max="20" size="small" style="width: 80px" />
            <n-button type="primary" :loading="searching" @click="handleSearchTest">开始检索</n-button>
          </div>
        </div>

        <div v-if="searchResults.length" class="search-results">
          <div v-for="(item, idx) in searchResults" :key="idx" class="search-result-item">
            <div class="result-header">
              <span class="result-source">{{ item.source }}</span>
              <n-tag size="small" type="info">相似度 {{ item.scoreLabel }}</n-tag>
            </div>
            <div class="result-content">{{ item.content }}</div>
          </div>
        </div>
        <n-empty v-else-if="searchTested" description="未检索到相关内容" size="small" style="margin-top: 16px" />
      </n-card>
    </div>

    <n-drawer v-model:show="drawerVisible" :width="480" placement="right">
      <n-drawer-content :title="detail?.filename || '文档详情'" closable>
        <n-spin :show="detailLoading">
          <template v-if="detail">
            <div class="detail-section">
              <h4>基础信息</h4>
              <n-descriptions :column="1" label-placement="left" size="small">
                <n-descriptions-item label="文件名">{{ detail.filename }}</n-descriptions-item>
                <n-descriptions-item label="文件大小">{{ detail.file_size_label }}</n-descriptions-item>
                <n-descriptions-item label="上传时间">{{ formatTime(detail.ingested_at) }}</n-descriptions-item>
                <n-descriptions-item label="上传人">{{ detail.operator_name }}</n-descriptions-item>
              </n-descriptions>
            </div>
            <div class="detail-section">
              <h4>知识信息</h4>
              <n-descriptions :column="1" label-placement="left" size="small">
                <n-descriptions-item label="Chunk 数量">{{ detail.chunk_count }}</n-descriptions-item>
                <n-descriptions-item label="向量数量">{{ detail.vector_count }}</n-descriptions-item>
                <n-descriptions-item label="分类">{{ detail.category }}</n-descriptions-item>
                <n-descriptions-item label="状态">
                  <n-tag :type="statusTagType(detail.status_label)" size="small">{{ detail.status_label }}</n-tag>
                </n-descriptions-item>
              </n-descriptions>
            </div>
            <div class="detail-section">
              <h4>Chunk 预览</h4>
              <div v-if="detail.chunk_previews?.length">
                <div
                  v-for="(chunk, i) in detail.chunk_previews"
                  :key="i"
                  class="chunk-preview"
                >
                  <div class="chunk-index">#{{ i + 1 }}</div>
                  <div class="chunk-text">{{ chunk }}</div>
                </div>
              </div>
              <n-empty v-else description="暂无 Chunk 内容" size="small" />
            </div>
          </template>
        </n-spin>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import type { DataTableColumns, UploadCustomRequestOptions } from 'naive-ui'
import {
  NButton,
  NCard,
  NDataTable,
  NDescriptions,
  NDescriptionsItem,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NGi,
  NGrid,
  NIcon,
  NInput,
  NInputNumber,
  NSpin,
  NStatistic,
  NTag,
  NUpload,
  useDialog,
  useMessage,
} from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import {
  deleteKnowledgeDocument,
  fetchKnowledgeDocumentDetail,
  fetchKnowledgeDocuments,
  fetchKnowledgeStats,
  ingestKnowledgeDirectory,
  rebuildKnowledgeIndex,
  searchKnowledge,
  uploadKnowledgeFile,
  type KnowledgeDocument,
  type KnowledgeDocumentDetail,
  type KnowledgeStats,
} from '@/api/knowledge'
import { useAuthStore } from '@/stores/auth'

const message = useMessage()
const dialog = useDialog()
const authStore = useAuthStore()

const loading = ref(false)
const uploading = ref(false)
const ingesting = ref(false)
const rebuilding = ref(false)
const searching = ref(false)
const searchTested = ref(false)
const detailLoading = ref(false)
const drawerVisible = ref(false)

const stats = ref<KnowledgeStats | null>(null)
const documents = ref<KnowledgeDocument[]>([])
const detail = ref<KnowledgeDocumentDetail | null>(null)

const searchKeyword = ref('')
const testQuery = ref('')
const testTopK = ref(5)
const searchResults = ref<Array<{ source: string; scoreLabel: string; content: string }>>([])

const isAdmin = computed(() => authStore.user?.roles?.includes('Admin') ?? false)

const lastUpdatedLabel = computed(() => {
  const t = stats.value?.last_updated
  if (!t) return '-'
  return formatTime(t)
})

const kbStatusType = computed(() => {
  const s = stats.value?.kb_status
  if (s === '正常') return 'success'
  if (s === '空库') return 'warning'
  return 'default'
})

const filteredDocuments = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  if (!kw) return documents.value
  return documents.value.filter(
    (d) =>
      d.filename.toLowerCase().includes(kw) ||
      d.category.toLowerCase().includes(kw) ||
      d.operator_name.toLowerCase().includes(kw),
  )
})

const columns = computed<DataTableColumns<KnowledgeDocument>>(() => {
  const base: DataTableColumns<KnowledgeDocument> = [
    { title: '文件名', key: 'filename', ellipsis: { tooltip: true }, minWidth: 180 },
    { title: '分类', key: 'category', width: 90 },
    { title: '文件大小', key: 'file_size_label', width: 100 },
    { title: 'Chunk 数量', key: 'chunk_count', width: 100 },
    { title: '上传人', key: 'operator_name', width: 100 },
    {
      title: '更新时间',
      key: 'updated_at',
      width: 170,
      render: (row) => formatTime(row.updated_at),
    },
    {
      title: '状态',
      key: 'status_label',
      width: 90,
      render: (row) =>
        h(NTag, { size: 'small', type: statusTagType(row.status_label), round: true }, () => row.status_label),
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      fixed: 'right',
      render: (row) =>
        h('div', { class: 'action-btns' }, [
          h(
            NButton,
            { size: 'small', quaternary: true, type: 'primary', onClick: () => openDetail(row) },
            { default: () => '查看详情' },
          ),
          isAdmin.value
            ? h(
                NButton,
                { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) },
                { default: () => '删除' },
              )
            : null,
        ]),
    },
  ]
  return base
})

function formatTime(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

function statusTagType(label: string) {
  if (label === '已完成') return 'success'
  if (label === '处理中') return 'warning'
  if (label === '失败') return 'error'
  return 'default'
}

async function loadData() {
  loading.value = true
  try {
    const [statsData, docsData] = await Promise.all([
      fetchKnowledgeStats(),
      fetchKnowledgeDocuments(),
    ])
    stats.value = statsData
    documents.value = docsData.items
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : '加载知识库失败')
  } finally {
    loading.value = false
  }
}

async function openDetail(row: KnowledgeDocument) {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await fetchKnowledgeDocumentDetail(row.doc_id)
  } catch {
    message.error('加载文档详情失败')
    drawerVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function handleUpload(options: UploadCustomRequestOptions) {
  if (!options.file.file) return
  uploading.value = true
  try {
    const result = await uploadKnowledgeFile(options.file.file)
    if (result.unchanged) {
      message.info('文档内容未变化，跳过导入')
    } else {
      message.success('文档上传成功')
    }
    await loadData()
    options.onFinish()
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : '上传失败')
    options.onError()
  } finally {
    uploading.value = false
  }
}

async function handleIngestDirectory() {
  ingesting.value = true
  try {
    const result = await ingestKnowledgeDirectory()
    message.success(`目录导入完成：${result.files} 个文件，${result.chunks} 个 chunk`)
    await loadData()
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : '目录导入失败')
  } finally {
    ingesting.value = false
  }
}

async function handleRebuild() {
  dialog.warning({
    title: '重建索引',
    content: '将重新扫描知识库目录并重建向量索引，可能需要一些时间，确定继续？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      rebuilding.value = true
      try {
        const result = await rebuildKnowledgeIndex()
        message.success(`索引重建完成：${result.files} 个文件，${result.chunks} 个 chunk`)
        await loadData()
      } catch (err: unknown) {
        message.error(err instanceof Error ? err.message : '重建索引失败')
      } finally {
        rebuilding.value = false
      }
    },
  })
}

async function handleDelete(row: KnowledgeDocument) {
  dialog.warning({
    title: '删除文档',
    content: `确定删除「${row.filename}」？相关向量索引将一并清除。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const result = await deleteKnowledgeDocument(row.doc_id)
        message.success(`已删除 ${result.filename}`)
        await loadData()
      } catch (err: unknown) {
        message.error(err instanceof Error ? err.message : '删除失败')
      }
    },
  })
}

async function handleSearchTest() {
  const query = testQuery.value.trim()
  if (!query) {
    message.warning('请输入测试问题')
    return
  }
  searching.value = true
  searchTested.value = true
  searchResults.value = []
  try {
    const result = await searchKnowledge(query, testTopK.value)
    if (result.rejected || !result.docs?.length) {
      searchResults.value = []
      return
    }
    searchResults.value = result.docs.map((doc) => {
      const meta = doc.metadata || {}
      const source = String(meta.source || meta.file_path || '未知文档')
      const score = doc.rerank_score ?? doc.score
      return {
        source,
        scoreLabel: score != null ? String(score) : '-',
        content: (doc.content || '').trim(),
      }
    })
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : '检索失败')
  } finally {
    searching.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.kb-page {
  padding: 24px;
  min-height: calc(100vh - 57px);
  box-sizing: border-box;
}
.kb-container {
  width: 100%;
}
.page-header {
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
}
.subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #888;
}
.stat-grid {
  margin-bottom: 20px;
}
.stat-card {
  border-radius: 14px;
}
.status-stat {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.stat-label {
  font-size: 14px;
  color: #888;
}
.table-card {
  border-radius: 14px;
  margin-bottom: 20px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.search-input {
  width: 280px;
}
.toolbar-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.search-test-card {
  border-radius: 14px;
}
.search-test-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.search-test-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}
.topk-label {
  font-size: 13px;
  color: #666;
}
.search-results {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.search-result-item {
  border: 1px solid #ececec;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fafafa;
}
.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.result-source {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}
.result-content {
  font-size: 13px;
  color: #555;
  line-height: 1.6;
  white-space: pre-wrap;
}
.detail-section {
  margin-bottom: 24px;
}
.detail-section h4 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}
.chunk-preview {
  border: 1px solid #ececec;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
  background: #fafafa;
}
.chunk-index {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}
.chunk-text {
  font-size: 13px;
  color: #444;
  line-height: 1.6;
  white-space: pre-wrap;
}
:deep(.action-btns) {
  display: flex;
  gap: 4px;
}
</style>
