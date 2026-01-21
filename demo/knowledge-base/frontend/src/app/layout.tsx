import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "企业智能知识库 | Enterprise Knowledge Base",
  description: "基于 AI 的企业级文档管理与智能问答系统",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="h-full">
      <body className={`${inter.className} h-full bg-background antialiased`}>
        {children}
      </body>
    </html>
  )
}
