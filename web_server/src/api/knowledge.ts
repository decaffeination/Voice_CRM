import http from './http'

export interface KnowledgeDocument {
  doc_id: string
  filename: string
  file_hash: string
  version: number
  chunk_count: number
  file_path: string
  status: string
  status_label: string
  category: string
  file_size: number
  file_size_label: string
  operator_user_id: number | null
  operator_name: string
  ingested_at: string | null
  updated_at: string | null
}

export interface KnowledgeDocumentDetail extends KnowledgeDocument {
  chunk_previews: string[]
  vector_count: number
}

export interface KnowledgeDocumentListResponse {
  items: KnowledgeDocument[]
  total: number
}

export interface KnowledgeStats {
  collection: string
  chroma_path: string
  docs_path: string
  chunk_count: number
  document_count: number
  last_updated: string | null
  kb_status: string
  top_k: number
  rerank_enabled: boolean
  hybrid_enabled: boolean
}

export interface KnowledgeSearchResult {
  query: string
  docs: Array<{
    id?: string
    content: string
    metadata?: Record<string, unknown>
    score?: number
    rerank_score?: number
  }>
  citations: Array<{
    index: number
    source: string
    snippet: string
    score?: number
  }>
  context: string
  rejected: boolean
  error?: string
  message?: string
}

export async function fetchKnowledgeStats() {
  const { data } = await http.get<KnowledgeStats>('/knowledge/stats')
  return data
}

export async function fetchKnowledgeDocuments() {
  const { data } = await http.get<KnowledgeDocumentListResponse>('/knowledge/docs')
  return data
}

export async function fetchKnowledgeDocumentDetail(docId: string) {
  const { data } = await http.get<KnowledgeDocumentDetail>(`/knowledge/docs/${docId}`)
  return data
}

export async function deleteKnowledgeDocument(docId: string) {
  const { data } = await http.delete<{ doc_id: string; filename: string; removed_chunks: number; status: string }>(
    `/knowledge/docs/${docId}`,
  )
  return data
}

export async function ingestKnowledgeDirectory() {
  const { data } = await http.post<{ result: Record<string, unknown> }>('/knowledge/ingest/directory')
  return data.result
}

export async function rebuildKnowledgeIndex() {
  const { data } = await http.post<{ result: Record<string, unknown> }>('/knowledge/rebuild')
  return data.result
}

export async function uploadKnowledgeFile(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post<{ result: Record<string, unknown> }>(
    '/knowledge/ingest/file',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data.result
}

export async function searchKnowledge(query: string, topK = 5) {
  const { data } = await http.post<KnowledgeSearchResult>('/knowledge/search', {
    query,
    top_k: topK,
  })
  return data
}
