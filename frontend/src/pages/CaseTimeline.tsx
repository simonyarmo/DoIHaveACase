import { useCallback, useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"

import { ChatPanel } from "@/components/ChatPanel"
import { ResearchProgress } from "@/components/ResearchProgress"
import { useCaseSocket } from "@/hooks/useCaseSocket"
import { getCase, getMessages } from "@/lib/api"
import type { ConversationMessageOut, ProgressEvent } from "@/types/case"

export function CaseTimeline() {
  const { id } = useParams<{ id: string }>()
  const caseId = id ?? null
  const queryClient = useQueryClient()
  const [extraMessages, setExtraMessages] = useState<ConversationMessageOut[]>([])

  const { data: caseData } = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => getCase(caseId!),
    enabled: !!caseId,
  })

  const { data: history } = useQuery({
    queryKey: ["messages", caseId],
    queryFn: () => getMessages(caseId!),
    enabled: !!caseId,
  })

  const handleProgress = useCallback(
    (event: ProgressEvent) => {
      if (event.tool === "assessment" && (event.status === "complete" || event.status === "error")) {
        void queryClient.invalidateQueries({ queryKey: ["case", caseId] })
      }
      void queryClient.invalidateQueries({ queryKey: ["messages", caseId] })
    },
    [caseId, queryClient]
  )

  const handleAssistantMessage = useCallback((content: string) => {
    setExtraMessages((prev) => [
      ...prev,
      {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        message_type: "text",
        content,
        form_schema: null,
        form_response: null,
        created_at: new Date().toISOString(),
      },
    ])
  }, [])

  const { progress, streamingContent, isStreaming, sendMessage, sendFormResponse } = useCaseSocket(caseId, {
    onProgress: handleProgress,
    onAssistantMessage: handleAssistantMessage,
  })

  // Once research finishes, the WS sends one final assistant token-stream as
  // well as new conversation_messages rows — drop the locally-buffered
  // messages once the server-side history has caught up.
  useEffect(() => {
    setExtraMessages([])
  }, [history])

  if (!caseId || !caseData) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">Loading…</div>
  }

  const { case: caseInfo, details } = caseData
  const isResearching = caseInfo.status === "researching"
  const hasLease = caseData.documents.some((d) => d.type === "lease")
  const messages = [...(history ?? []), ...extraMessages]

  const handleSend = (content: string) => {
    setExtraMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: "user",
        message_type: "text",
        content,
        form_schema: null,
        form_response: null,
        created_at: new Date().toISOString(),
      },
    ])
    sendMessage(content)
  }

  const handleFormResponse = (formResponse: Record<string, unknown>) => {
    setExtraMessages((prev) => [
      ...prev,
      {
        id: `form-response-${Date.now()}`,
        role: "user",
        message_type: "form_response",
        content: null,
        form_schema: null,
        form_response: formResponse,
        created_at: new Date().toISOString(),
      },
    ])
    sendFormResponse(formResponse)
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 space-y-4 overflow-y-auto p-6">
        <div>
          <h1 className="text-xl font-semibold">{details.property_address ?? "Your case"}</h1>
          <p className="text-sm text-muted-foreground">
            Status: <span className="font-medium text-foreground">{caseInfo.status.replace(/_/g, " ")}</span>
          </p>
        </div>

        {isResearching && <ResearchProgress progress={progress} hasLease={hasLease} />}

        {!isResearching && (
          <div className="space-y-1 rounded-md border border-border p-4 text-sm">
            <h2 className="font-medium">Case overview</h2>
            {details.violation_confirmed != null && (
              <p>
                {details.violation_confirmed
                  ? `Your landlord appears to be in violation — ${details.days_overdue ?? 0} day(s) overdue.`
                  : "No deadline violation confirmed yet."}
              </p>
            )}
            {details.deadline_date && <p className="text-muted-foreground">Deadline: {details.deadline_date}</p>}
            {details.landlord_sos_verified && (
              <p className="text-muted-foreground">Landlord verified as {details.landlord_legal_name}.</p>
            )}
          </div>
        )}
      </div>

      <div className="flex w-96 flex-col border-l border-border">
        <ChatPanel
          messages={messages}
          streamingContent={streamingContent}
          isStreaming={isStreaming}
          onSend={handleSend}
          onFormResponse={handleFormResponse}
          disabled={isResearching}
        />
      </div>
    </div>
  )
}
