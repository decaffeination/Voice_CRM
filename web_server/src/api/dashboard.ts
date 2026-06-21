import http from './http'

export interface DashboardOverview {
  overview: {
    today_sessions: number
    total_sessions: number
    knowledge_documents: number
    customer_count: number
    ai_answer_count: number
    today_ai_answers: number
    online_users: number
    system_status: string
  }
  ai_runtime: {
    today_qa_count: number
    total_qa_count: number
    knowledge_hit_rate: number | null
    knowledge_miss_count: number
    avg_response_time_ms: number | null
    token_consumption: number | null
  }
  knowledge: {
    document_count: number
    chunk_count: number
    last_updated: string | null
    kb_status: string
    recent_documents: Array<{
      doc_id: string
      filename: string
      chunk_count: number
      updated_at: string | null
    }>
    popular_documents: Array<{
      doc_id: string
      filename: string
      chunk_count: number
    }>
  }
  crm: {
    customer_count: number
    new_customers_week: number
    pending_followups: number
    recent_followups: Array<{
      id: number
      customer_id: number
      customer_name: string
      content: string
      created_at: string | null
    }>
  }
  recent_activities: Array<{
    type: string
    label: string
    description: string
    user_name: string
    created_at: string | null
  }>
  system_status: Array<{
    name: string
    key: string
    status: string
  }>
}

export async function fetchDashboardOverview() {
  const { data } = await http.get<DashboardOverview>('/dashboard/overview')
  return data
}
