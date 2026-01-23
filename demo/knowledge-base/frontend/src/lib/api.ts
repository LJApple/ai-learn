import axios from "axios"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  sources?: Source[]
}

export interface Source {
  document_id: string
  chunk_id?: string
  score: number
  rerank_score?: number
  title?: string
  html_content?: string
  has_images?: boolean
}

export interface ChatResponse {
  id: string
  answer: string
  sources: Source[]
  conversation_id: string
  has_context: boolean
}

export interface Conversation {
  id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface Document {
  id: string
  title: string
  source_type: string
  status: string
  chunk_count: number
  permission_level?: string
  created_at: string
  updated_at: string
}

export const chatApi = {
  sendMessage: async (
    query: string,
    conversationId?: string,
    options?: { top_k?: number; score_threshold?: number; use_rerank?: boolean }
  ): Promise<ChatResponse> => {
    const { data } = await api.post("/chat/completions", {
      query,
      conversation_id: conversationId,
      ...options,
    })
    return data
  },

  getConversations: async (): Promise<Conversation[]> => {
    const { data } = await api.get("/conversations")
    return data
  },

  getConversation: async (id: string): Promise<ChatMessage[]> => {
    const { data } = await api.get(`/conversations/${id}`)
    return data
  },

  deleteConversation: async (id: string): Promise<void> => {
    await api.delete(`/conversations/${id}`)
  },
}

export const documentApi = {
  upload: async (
    file: File,
    metadata: { title: string; source_type: string; permission_level?: string }
  ): Promise<{ document_id: string; status: string; message: string }> => {
    const formData = new FormData()
    formData.append("file", file)
    formData.append("title", metadata.title)
    formData.append("source_type", metadata.source_type)
    if (metadata.permission_level) {
      formData.append("permission_level", metadata.permission_level)
    }

    const { data } = await api.post("/documents/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    })
    return data
  },

  list: async (): Promise<{ items: Document[]; total: number }> => {
    const { data } = await api.get("/documents")
    return data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/documents/${id}`)
  },

  reindex: async (id: string): Promise<any> => {
    const { data } = await api.post(`/documents/${id}/reindex`)
    return data
  },
}
