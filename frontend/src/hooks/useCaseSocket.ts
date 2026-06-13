import { useCallback, useEffect, useRef, useState } from "react"

import { getCaseSocketUrl } from "@/lib/api"
import type { ProgressEvent, WsServerMessage } from "@/types/case"

interface UseCaseSocketHandlers {
  onProgress?: (event: ProgressEvent) => void
  /** Called once a streamed assistant reply finishes, with the full text. */
  onAssistantMessage?: (content: string) => void
}

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
    let ws: WebSocket | undefined
    let cancelled = false

    void (async () => {
      const url = await getCaseSocketUrl(caseId)
      if (cancelled) return

      ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => setConnected(false)
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
    })()

    return () => {
      cancelled = true
      ws?.close()
      wsRef.current = null
      setConnected(false)
    }
  }, [caseId])

  const sendMessage = useCallback((content: string) => {
    wsRef.current?.send(JSON.stringify({ type: "message", content }))
  }, [])

  const sendFormResponse = useCallback((formResponse: Record<string, unknown>) => {
    wsRef.current?.send(JSON.stringify({ type: "form_response", form_response: formResponse }))
  }, [])

  return { connected, progress, streamingContent, isStreaming, sendMessage, sendFormResponse }
}
