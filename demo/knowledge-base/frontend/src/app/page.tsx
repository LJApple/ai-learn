"use client"

import { useState, useEffect, useRef } from "react"
import { 
  Send, 
  FileText, 
  MessageSquare, 
  Upload, 
  Plus, 
  Trash2, 
  Sparkles, 
  Loader2, 
  ChevronLeft, 
  ChevronRight,
  ThumbsUp, 
  ThumbsDown, 
  Check, 
  X, 
  Clock, 
  Search, 
  FolderOpen, 
  Brain, 
  Zap, 
  MoreVertical,
  Settings,
  Menu,
  LayoutGrid,
  List as ListIcon
} from "lucide-react"
import { chatApi, documentApi, ChatMessage, Conversation, Document, Source } from "@/lib/api"
import ReactMarkdown from "react-markdown"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

export default function HomePage() {
  // State
  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<"chat" | "documents">("chat")
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversation, setCurrentConversation] = useState<string | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [streamingAnswer, setStreamingAnswer] = useState("")
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [uploadMetadata, setUploadMetadata] = useState({ title: "", sourceType: "", permissionLevel: "public" })
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [feedbackMap, setFeedbackMap] = useState<Record<string, 1 | -1>>({})
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid")

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Effects
  useEffect(() => {
    loadConversations()
    loadDocuments()
  }, [])

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, streamingAnswer])

  useEffect(() => {
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }, [query])

  // Data Loading
  const loadConversations = async () => {
    try {
      const data = await chatApi.getConversations()
      setConversations(data)
    } catch (error) {
      console.error("Failed to load conversations:", error)
    }
  }

  const loadDocuments = async () => {
    try {
      const data = await documentApi.list()
      setDocuments(data.items)
    } catch (error) {
      console.error("Failed to load documents:", error)
    }
  }

  // Chat Handlers
  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!query.trim() || loading) return

    const userMessage: ChatMessage = { role: "user", content: query }
    setMessages((prev) => [...prev, userMessage])
    setQuery("")
    if (textareaRef.current) textareaRef.current.style.height = "auto"
    
    setLoading(true)
    setStreamingAnswer("")
    setSources([])

    try {
      const response = await chatApi.sendMessage(query, currentConversation || undefined, {
        top_k: 10,
        score_threshold: 0.3,
        use_rerank: false,
      })

      const answer = response.answer
      // Simulate streaming for better UX
      for (let i = 0; i < answer.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 5))
        setStreamingAnswer((prev) => prev + answer[i])
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: answer },
      ])
      setStreamingAnswer("")
      setSources(response.sources)

      if (response.conversation_id && response.conversation_id !== currentConversation) {
        setCurrentConversation(response.conversation_id)
        loadConversations()
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "抱歉，遇到了一些技术问题，请稍后重试。" },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setCurrentConversation(null)
    setStreamingAnswer("")
    setQuery("")
    setSources([])
    if (window.innerWidth < 1024) setSidebarOpen(false)
  }

  const handleSelectConversation = async (id: string) => {
    try {
      const history = await chatApi.getConversation(id)
      setMessages(history)
      setCurrentConversation(id)
      setSources([])
      if (window.innerWidth < 1024) setSidebarOpen(false)
    } catch (error) {
      console.error("Failed to load conversation:", error)
    }
  }

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await chatApi.deleteConversation(id)
      loadConversations()
      if (currentConversation === id) {
        handleNewChat()
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error)
    }
  }

  // Document Handlers
  const handleFileSelect = (file: File) => {
    setUploadMetadata({
      title: file.name,
      sourceType: file.name.split(".").pop() || "unknown",
      permissionLevel: "public"
    })
    setShowUploadModal(true)
  }

  const handleFileUpload = async () => {
    const file = fileInputRef.current?.files?.[0]
    if (!file) return

    setUploading(true)
    setUploadProgress(0)
    setShowUploadModal(false)

    try {
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 200)

      await documentApi.upload(file, {
        title: uploadMetadata.title || file.name,
        source_type: uploadMetadata.sourceType || file.name.split(".").pop() || "unknown",
        permission_level: uploadMetadata.permissionLevel,
      })

      clearInterval(progressInterval)
      setUploadProgress(100)
      setTimeout(() => {
        setUploadProgress(0)
        setUploading(false)
        loadDocuments()
      }, 500)
    } catch (error) {
      setUploading(false)
      setUploadProgress(0)
      console.error("Failed to upload file:", error)
    }
  }

  const handleDeleteDocument = async (id: string) => {
    try {
      await documentApi.delete(id)
      loadDocuments()
    } catch (error) {
      console.error("Failed to delete document:", error)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      if (fileInputRef.current) {
        const dt = new DataTransfer()
        dt.items.add(file)
        fileInputRef.current.files = dt.files
      }
      handleFileSelect(file)
    }
  }

  // UI Helpers
  const getLastAssistantMessageIndex = () => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return i
    }
    return -1
  }

  const handleFeedback = (messageIndex: number, feedback: 1 | -1) => {
    const messageId = `${currentConversation || "new"}-${messageIndex}`
    setFeedbackMap((prev) => ({ ...prev, [messageId]: feedback }))
  }

  return (
    <TooltipProvider>
      <div className="flex h-screen bg-background overflow-hidden">
        {/* Sidebar */}
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-50 w-72 bg-muted/40 border-r transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 flex flex-col",
            !sidebarOpen && "-translate-x-full lg:w-0 lg:border-none"
          )}
        >
          {/* Sidebar Header */}
          <div className="h-16 flex items-center px-4 border-b bg-background/50 backdrop-blur-sm">
            <div className="flex items-center gap-2 font-semibold text-lg tracking-tight">
              <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                <Brain className="h-5 w-5" />
              </div>
              企业知识库
            </div>
            <Button 
              variant="ghost" 
              size="icon" 
              className="ml-auto lg:hidden"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* New Chat Button */}
          <div className="p-4">
            <Button
              onClick={handleNewChat}
              className="w-full justify-start shadow-sm bg-background hover:bg-accent border text-foreground"
              variant="outline"
            >
              <Plus className="h-4 w-4 mr-2" />
              新建对话
            </Button>
          </div>

          {/* Navigation */}
          <ScrollArea className="flex-1 px-4">
            <div className="space-y-4 py-2">
              <div className="px-2 text-xs font-medium text-muted-foreground">最近对话</div>
              <div className="space-y-1">
                {conversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                    className={cn(
                      "group w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                      currentConversation === conv.id
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <MessageSquare className="h-4 w-4" />
                    <span className="flex-1 truncate text-left">{conv.title || "新对话"}</span>
                    <div 
                      className={cn(
                        "opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-background",
                        currentConversation === conv.id && "opacity-100"
                      )}
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                    >
                      <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                    </div>
                  </button>
                ))}
                {conversations.length === 0 && (
                  <div className="px-3 py-4 text-center text-sm text-muted-foreground bg-muted/30 rounded-lg border border-dashed">
                    暂无历史记录
                  </div>
                )}
              </div>
            </div>
          </ScrollArea>

          {/* Sidebar Footer */}
          <div className="p-4 border-t bg-background/50 backdrop-blur-sm space-y-2">
            <Button
              variant={activeTab === "documents" ? "secondary" : "ghost"}
              className="w-full justify-start"
              onClick={() => setActiveTab("documents")}
            >
              <FolderOpen className="h-4 w-4 mr-2" />
              知识库管理
            </Button>
            <div className="flex items-center gap-2 px-2 py-1.5 text-xs text-muted-foreground">
              <Settings className="h-3.5 w-3.5" />
              <span>v1.0.0</span>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0 bg-background">
          {/* Header */}
          <header className="h-16 flex items-center justify-between px-6 border-b bg-background/80 backdrop-blur-md sticky top-0 z-20">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                className={cn("-ml-2", sidebarOpen && "lg:hidden")}
                onClick={() => setSidebarOpen(!sidebarOpen)}
              >
                {sidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              </Button>
              <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-auto">
                <TabsList className="grid w-full grid-cols-2 h-9">
                  <TabsTrigger value="chat">智能问答</TabsTrigger>
                  <TabsTrigger value="documents">文档库</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
            
            <div className="flex items-center gap-2">
              <div className="hidden sm:flex items-center text-sm text-muted-foreground bg-muted/50 px-3 py-1 rounded-full">
                <Zap className="h-3.5 w-3.5 mr-1.5 text-amber-500 fill-amber-500" />
                <span>RAG 模型已就绪</span>
              </div>
            </div>
          </header>

          {/* Chat View */}
          {activeTab === "chat" && (
            <div className="flex-1 flex flex-col min-h-0 relative">
              <ScrollArea className="flex-1 p-4 md:p-8">
                <div className="max-w-3xl mx-auto space-y-8 pb-20">
                  {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-8">
                      <div className="relative">
                        <div className="absolute inset-0 bg-primary/20 blur-3xl rounded-full" />
                        <div className="relative bg-background p-6 rounded-2xl shadow-xl border">
                          <Brain className="h-12 w-12 text-primary" />
                        </div>
                      </div>
                      <div className="space-y-2 max-w-md">
                        <h2 className="text-2xl font-bold tracking-tight">欢迎使用企业智能助手</h2>
                        <p className="text-muted-foreground">
                          我可以帮您快速检索企业文档，回答业务问题，并提供可信的来源参考。
                        </p>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-lg">
                        {[
                          "如何申请年假？",
                          "公司的报销流程是怎样的？",
                          "最新的产品手册在哪里？",
                          "查看上季度的销售报告"
                        ].map((q, i) => (
                          <button
                            key={i}
                            onClick={() => {
                              setQuery(q)
                              // Optional: Auto submit
                            }}
                            className="flex items-center gap-2 p-3 text-sm text-left bg-muted/50 hover:bg-muted rounded-xl border border-transparent hover:border-border transition-all"
                          >
                            <MessageSquare className="h-4 w-4 text-muted-foreground" />
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <>
                      {messages.map((message, index) => (
                        <div
                          key={index}
                          className={cn(
                            "flex gap-4 w-full",
                            message.role === "user" ? "justify-end" : "justify-start"
                          )}
                        >
                          {message.role === "assistant" && (
                            <Avatar className="h-8 w-8 mt-1 border bg-primary/5">
                              <AvatarFallback><Brain className="h-4 w-4 text-primary" /></AvatarFallback>
                            </Avatar>
                          )}
                          <div className={cn("flex flex-col max-w-[85%]", message.role === "user" && "items-end")}>
                            <div
                              className={cn(
                                "px-5 py-3.5 rounded-2xl text-sm shadow-sm",
                                message.role === "user"
                                  ? "bg-primary text-primary-foreground rounded-br-sm"
                                  : "bg-card border rounded-bl-sm"
                              )}
                            >
                              <div className={cn(
                                "prose prose-sm max-w-none break-words",
                                message.role === "user" ? "prose-invert" : "dark:prose-invert"
                              )}>
                                <ReactMarkdown>{message.content}</ReactMarkdown>
                              </div>
                            </div>

                            {/* Assistant Actions */}
                            {message.role === "assistant" && (
                              <div className="flex items-center gap-1 mt-1 ml-1">
                                <Button 
                                  variant="ghost" 
                                  size="icon" 
                                  className={cn("h-6 w-6", feedbackMap[`${currentConversation}-${index}`] === 1 && "text-green-600")}
                                  onClick={() => handleFeedback(index, 1)}
                                >
                                  <ThumbsUp className="h-3.5 w-3.5" />
                                </Button>
                                <Button 
                                  variant="ghost" 
                                  size="icon" 
                                  className={cn("h-6 w-6", feedbackMap[`${currentConversation}-${index}`] === -1 && "text-red-600")}
                                  onClick={() => handleFeedback(index, -1)}
                                >
                                  <ThumbsDown className="h-3.5 w-3.5" />
                                </Button>
                              </div>
                            )}
                          </div>
                          {message.role === "user" && (
                            <Avatar className="h-8 w-8 mt-1 border bg-muted">
                              <AvatarFallback>Me</AvatarFallback>
                            </Avatar>
                          )}
                        </div>
                      ))}

                      {/* Streaming State */}
                      {streamingAnswer && (
                        <div className="flex gap-4 w-full">
                          <Avatar className="h-8 w-8 mt-1 border bg-primary/5">
                            <AvatarFallback><Brain className="h-4 w-4 text-primary" /></AvatarFallback>
                          </Avatar>
                          <div className="flex flex-col max-w-[85%]">
                            <div className="px-5 py-3.5 rounded-2xl rounded-bl-sm bg-card border text-sm shadow-sm">
                              <div className="prose prose-sm max-w-none dark:prose-invert">
                                <ReactMarkdown>{streamingAnswer}</ReactMarkdown>
                                <span className="inline-block w-2 h-4 ml-1 align-middle bg-primary animate-pulse" />
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Loading State */}
                      {loading && !streamingAnswer && (
                        <div className="flex gap-4 w-full">
                          <Avatar className="h-8 w-8 mt-1 border bg-primary/5">
                            <AvatarFallback><Brain className="h-4 w-4 text-primary" /></AvatarFallback>
                          </Avatar>
                          <div className="flex items-center gap-2 px-5 py-3.5 rounded-2xl rounded-bl-sm bg-card border text-sm shadow-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            正在分析文档库...
                          </div>
                        </div>
                      )}
                      
                      <div ref={messagesEndRef} className="h-4" />
                    </>
                  )}
                </div>
              </ScrollArea>

              {/* Sources Panel - Always visible if sources exist */}
              {sources.length > 0 && (
                <div className="border-t bg-muted/20 px-4 py-3">
                  <div className="max-w-3xl mx-auto">
                    <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      <FileText className="h-3 w-3" />
                      参考来源
                    </div>
                    <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
                      {sources.map((source, i) => (
                        <div 
                          key={i} 
                          className="flex-shrink-0 w-60 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors cursor-pointer group"
                        >
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                              <FileText className="h-3.5 w-3.5" />
                            </div>
                            <Badge variant="secondary" className="text-[10px] h-5">
                              {(source.score * 100).toFixed(0)}% 匹配
                            </Badge>
                          </div>
                          <div className="text-xs font-medium line-clamp-2 mb-1" title={source.document_id}>
                            文档 ID: {source.document_id.slice(0, 8)}...
                          </div>
                          <div className="text-[10px] text-muted-foreground">
                            分块 ID: {source.chunk_id ? source.chunk_id.slice(0, 8) : 'N/A'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Input Area */}
              <div className="p-4 bg-background border-t">
                <div className="max-w-3xl mx-auto relative">
                  <div className={cn(
                    "relative flex items-end gap-2 p-2 rounded-2xl border bg-background shadow-sm transition-all ring-offset-background",
                    "focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2"
                  )}>
                    <Textarea
                      ref={textareaRef}
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="输入问题..."
                      className="min-h-[44px] max-h-[200px] w-full resize-none border-0 bg-transparent focus-visible:ring-0 px-3 py-2.5 scrollbar-thin"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault()
                          handleSubmit(e)
                        }
                      }}
                    />
                    <Button
                      size="icon"
                      className="h-9 w-9 mb-1 flex-shrink-0 rounded-xl transition-all"
                      disabled={!query.trim() || loading}
                      onClick={handleSubmit}
                    >
                      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    </Button>
                  </div>
                  <div className="mt-2 text-center text-xs text-muted-foreground">
                    AI 生成的内容可能不准确，请核对重要信息。
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Documents View */}
          {activeTab === "documents" && (
            <div className="flex-1 flex flex-col min-h-0 bg-muted/10">
              <div className="flex-1 overflow-auto p-6 md:p-10">
                <div className="max-w-6xl mx-auto space-y-8">
                  {/* Stats / Header */}
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                      <h2 className="text-2xl font-bold tracking-tight">文档库</h2>
                      <p className="text-muted-foreground">
                        管理已索引的 {documents.length} 个文档，共 {documents.reduce((acc, doc) => acc + (doc.chunk_count || 0), 0)} 个知识分块
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="bg-card border rounded-lg p-1 flex items-center">
                        <Button
                          variant={viewMode === "grid" ? "secondary" : "ghost"}
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => setViewMode("grid")}
                        >
                          <LayoutGrid className="h-4 w-4" />
                        </Button>
                        <Button
                          variant={viewMode === "list" ? "secondary" : "ghost"}
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => setViewMode("list")}
                        >
                          <ListIcon className="h-4 w-4" />
                        </Button>
                      </div>
                      <Button onClick={() => fileInputRef.current?.click()} className="gap-2">
                        <Upload className="h-4 w-4" />
                        上传文档
                      </Button>
                      <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        accept=".pdf,.doc,.docx,.txt,.md"
                        onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                      />
                    </div>
                  </div>

                  {/* Drag Drop Zone */}
                  {dragActive && (
                    <div 
                      className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center"
                      onDragEnter={handleDrag}
                      onDragLeave={handleDrag}
                      onDragOver={handleDrag}
                      onDrop={handleDrop}
                    >
                      <div className="bg-card p-10 rounded-3xl border-4 border-dashed border-primary shadow-2xl text-center animate-in zoom-in duration-300">
                        <Upload className="h-20 w-20 text-primary mx-auto mb-6" />
                        <h3 className="text-2xl font-bold mb-2">释放文件以添加</h3>
                        <p className="text-muted-foreground">松开鼠标即可自动开始上传处理</p>
                      </div>
                    </div>
                  )}

                  {/* Documents Grid/List */}
                  {documents.length === 0 ? (
                    <Card className="border-dashed">
                      <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                        <div className="p-4 rounded-full bg-muted mb-4">
                          <FolderOpen className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-semibold mb-1">暂无文档</h3>
                        <p className="text-muted-foreground mb-6 max-w-sm">
                          上传您的第一份文档，AI 将自动分析并建立索引。
                        </p>
                        <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
                          选择文件
                        </Button>
                      </CardContent>
                    </Card>
                  ) : (
                    <div className={cn(
                      "grid gap-4",
                      viewMode === "grid" ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" : "grid-cols-1"
                    )}>
                      {documents.map((doc) => (
                        <Card key={doc.id} className="group hover:shadow-md transition-all">
                          <CardContent className="p-5">
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex items-center gap-3">
                                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold text-xs uppercase">
                                  {doc.source_type}
                                </div>
                                <div>
                                  <div className="font-semibold line-clamp-1" title={doc.title}>
                                    {doc.title}
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    {new Date(doc.created_at).toLocaleDateString()}
                                  </div>
                                </div>
                              </div>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                                      onClick={() => handleDeleteDocument(doc.id)}
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>删除文档</TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                            
                            <Separator className="mb-4" />
                            
                            <div className="flex items-center justify-between text-xs">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="font-normal">
                                  {doc.chunk_count || 0} 分块
                                </Badge>
                                <Badge variant="secondary" className="font-normal capitalize">
                                  {doc.permission_level || "public"}
                                </Badge>
                              </div>
                              <div className={cn(
                                "flex items-center gap-1.5 font-medium",
                                doc.status === "ready" ? "text-emerald-600" : "text-amber-600"
                              )}>
                                <span className={cn(
                                  "h-1.5 w-1.5 rounded-full",
                                  doc.status === "ready" ? "bg-emerald-600" : "bg-amber-600 animate-pulse"
                                )} />
                                {doc.status === "ready" ? "已就绪" : "处理中"}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Upload Modal */}
        <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>上传文档</DialogTitle>
              <DialogDescription>
                设置文档属性以开始索引处理
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label className="text-sm font-medium">标题</label>
                <Input
                  value={uploadMetadata.title}
                  onChange={(e) => setUploadMetadata({ ...uploadMetadata, title: e.target.value })}
                  placeholder="文档标题"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">类型</label>
                  <select
                    value={uploadMetadata.sourceType}
                    onChange={(e) => setUploadMetadata({ ...uploadMetadata, sourceType: e.target.value })}
                    className="w-full px-3 py-2 bg-background border rounded-md text-sm"
                  >
                    <option value="pdf">PDF</option>
                    <option value="docx">Word (DOCX)</option>
                    <option value="txt">Text</option>
                    <option value="md">Markdown</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">权限</label>
                  <select
                    value={uploadMetadata.permissionLevel}
                    onChange={(e) => setUploadMetadata({ ...uploadMetadata, permissionLevel: e.target.value })}
                    className="w-full px-3 py-2 bg-background border rounded-md text-sm"
                  >
                    <option value="public">公开可见</option>
                    <option value="department">部门内部</option>
                    <option value="private">仅自己可见</option>
                  </select>
                </div>
              </div>
            </div>
            
            {uploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span>上传进度</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="h-1" />
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowUploadModal(false)} disabled={uploading}>
                取消
              </Button>
              <Button onClick={handleFileUpload} disabled={uploading}>
                {uploading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Upload className="h-4 w-4 mr-2" />}
                开始上传
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  )
}
