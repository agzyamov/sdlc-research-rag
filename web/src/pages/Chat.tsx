import { AssistantRuntimeProvider } from '@assistant-ui/react'
import { useDataStreamRuntime } from '@assistant-ui/react-data-stream'
import { Thread } from '@/components/assistant-ui/elements/thread.aui'
import { userHeaders } from '@/lib/api'

/** assistant-ui chat on the API's data stream: answer text, then cited papers as sources.
 * Remounted per user (key) so a conversation never mixes two users' access rights. */
export default function ChatPage({ user }: { user: string }) {
  const runtime = useDataStreamRuntime({
    api: '/api/chat',
    protocol: 'data-stream',
    headers: userHeaders(user),
  })
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="h-full">
        <Thread />
      </div>
    </AssistantRuntimeProvider>
  )
}
