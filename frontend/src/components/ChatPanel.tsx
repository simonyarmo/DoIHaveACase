import { useEffect, useRef, useState, type FormEvent } from "react"
import { Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import type { ConversationMessageOut } from "@/types/case"
import { DynamicForm } from "./DynamicForm"

interface ChatPanelProps {
  messages: ConversationMessageOut[]
  streamingContent: string
  isStreaming: boolean
  onSend: (content: string) => void
  onFormResponse: (formResponse: Record<string, unknown>) => void
  disabled?: boolean
}

export function ChatPanel({ messages, streamingContent, isStreaming, onSend, onFormResponse, disabled }: ChatPanelProps) {
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, streamingContent])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const content = input.trim()
    if (!content) return
    onSend(content)
    setInput("")
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && !isStreaming && (
          <p className="text-sm text-muted-foreground">Updates from your research agent will appear here.</p>
        )}

        {messages.map((message) => (
          <MessageItem key={message.id} message={message} onFormResponse={onFormResponse} />
        ))}

        {isStreaming && streamingContent && (
          <Bubble role="assistant">
            <p className="whitespace-pre-wrap">{streamingContent}</p>
          </Bubble>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border p-3">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={disabled ? "Chat opens once research completes…" : "Ask a question about your case…"}
          disabled={disabled}
        />
        <Button type="submit" size="default" disabled={disabled || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  )
}

function MessageItem({
  message,
  onFormResponse,
}: {
  message: ConversationMessageOut
  onFormResponse: (formResponse: Record<string, unknown>) => void
}) {
  if (message.message_type === "progress") {
    return <p className="text-center text-xs text-muted-foreground">{message.content}</p>
  }

  if (message.message_type === "dynamic_form" && message.form_schema) {
    return <DynamicForm schema={message.form_schema} onSubmit={onFormResponse} />
  }

  if (message.message_type === "form_response") {
    return (
      <Bubble role="user">
        <p className="text-sm italic">Submitted form response</p>
      </Bubble>
    )
  }

  const role = message.role === "user" ? "user" : "assistant"
  return (
    <Bubble role={role}>
      <p className="whitespace-pre-wrap">{message.content}</p>
    </Bubble>
  )
}

function Bubble({ role, children }: { role: "user" | "assistant"; children: React.ReactNode }) {
  return (
    <div className={cn("flex", role === "user" ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2 text-sm",
          role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
        )}
      >
        {children}
      </div>
    </div>
  )
}
