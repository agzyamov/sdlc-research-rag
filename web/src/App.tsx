import { parseAsString, parseAsStringLiteral, useQueryState } from 'nuqs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { usePrincipals } from '@/lib/api'
import ChatPage from '@/pages/Chat'
import EvaluationPage from '@/pages/Evaluation'
import GraphPage from '@/pages/KnowledgeGraph'
import LandscapePage from '@/pages/Landscape'

const TABS = ['chat', 'landscape', 'graph', 'eval'] as const

export default function App() {
  // Tab and demo user live in the URL, like the drill-through selection (shareable views).
  const [user, setUser] = useQueryState('user', parseAsString.withDefault('alice'))
  const [tab, setTab] = useQueryState('tab', parseAsStringLiteral(TABS).withDefault('chat'))
  const principals = usePrincipals({ query: { select: (r) => r.data } })
  const current = principals.data?.find((p) => p.id === user)

  return (
    <div className="bg-background text-foreground flex h-dvh flex-col">
      <header className="flex flex-wrap items-center gap-3 border-b px-4 py-2">
        <h1 className="text-base font-semibold tracking-tight">SDLC Research RAG</h1>
        <span className="text-muted-foreground hidden text-sm sm:inline">
          AI in software engineering, from arXiv
        </span>
        <div className="ml-auto flex items-center gap-2 text-sm">
          <span className="text-muted-foreground hidden md:inline">{current?.description}</span>
          <Select value={user} onValueChange={(v) => v && setUser(String(v))}>
            <SelectTrigger className="w-32" aria-label="Demo user">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(principals.data ?? [{ id: 'alice', description: '', groups: [] }]).map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </header>
      <main className="flex min-h-0 flex-1 flex-col">
      <Tabs
        value={tab}
        onValueChange={(v) => setTab(v as (typeof TABS)[number])}
        className="flex min-h-0 flex-1 flex-col gap-0"
      >
        <TabsList className="mx-4 mt-2">
          <TabsTrigger value="chat">Chat</TabsTrigger>
          <TabsTrigger value="landscape">Landscape</TabsTrigger>
          <TabsTrigger value="graph">Knowledge graph</TabsTrigger>
          <TabsTrigger value="eval">Evaluation</TabsTrigger>
        </TabsList>
        <TabsContent value="chat" className="min-h-0 flex-1">
          <ChatPage key={user} user={user} />
        </TabsContent>
        <TabsContent value="landscape" className="min-h-0 flex-1 overflow-auto">
          <LandscapePage user={user} />
        </TabsContent>
        <TabsContent value="graph" className="min-h-0 flex-1">
          <GraphPage user={user} />
        </TabsContent>
        <TabsContent value="eval" className="min-h-0 flex-1 overflow-auto">
          <EvaluationPage />
        </TabsContent>
      </Tabs>
      </main>
    </div>
  )
}
