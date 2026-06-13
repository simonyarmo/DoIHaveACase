import { useCallback, useEffect, useRef, useState } from "react"

import { getCaseSocketUrl } from "@/lib/api"
import type { ProgressEvent, WsServerMessage } from "@/types/case"

interface UseCaseSocketHandlers {
  onProgress?: (event: ProgressEvent) => void
  /** Called once a streamed assistant reply finishes, with the full text. */
  onAssistantMessage?: (content: string) => void
}

const RECONNECT_DELAY_MS = 2000

/** Single WebSocket connection to /ws/cases/{case_id} — relays research
 * progress events and drives the chat panel's token stream. */
export function useCaseSocket(caseId: string | null, handlers: UseCaseSocketHandlers = {}) {
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const [progress, setProgress] = useState<Record<string, ProgressEvent>>({})
  const [streamingContent, setStreamingContent] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)

  useEffect(() => {
    if (!caseId) return
    let cancelled = false
    let reconnectTimeout: ReturnType<typeof setTimeout> | undefined

    const connect = async () => {
      try {
        const url = await getCaseSocketUrl(caseId)
        if (cancelled) return

        const ws = new WebSocket(url)
        wsRef.current = ws

        ws.onopen = () => setConnected(true)
        ws.onclose = () => {
          setConnected(false)
          wsRef.current = null
          // The socket can drop for transient reasons (idle timeout, server
          // restart, network blip) — retry rather than leaving `connected`
          // permanently false with no recovery path.
          if (!cancelled) reconnectTimeout = setTimeout(connect, RECONNECT_DELAY_MS)
        }
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data) as WsServerMessage
          if ("tool" in data) {
            setProgress((prev) => ({ ...prev, [data.tool]: data }))
            handlersRef.current.onProgress?.(data)
          } else if (data.type === "token") {
            setIsStreaming(true)
            setStreamingContent((prev) => prev + data.content)
          } else if (data.type === "done") {
            setIsStreaming(false)
            setStreamingContent((prev) => {
              if (prev) handlersRef.current.onAssistantMessage?.(prev)
              return ""
            })
          }
        }
      } catch {
        if (!cancelled) reconnectTimeout = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    void connect()

    return () => {
      cancelled = true
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      wsRef.current?.close()
      wsRef.current = null
      setConnected(false)
    }
  }, [caseId])

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "message", content }))
    }
  }, [])

  const sendFormResponse = useCallback((formResponse: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "form_response", form_response: formResponse }))
    }
  }, [])

  return { connected, progress, streamingContent, isStreaming, sendMessage, sendFormResponse }
}
