import { AgentActivityPanel } from './components/AgentActivityPanel'
import { AuditPanel } from './components/AuditPanel'
import { QueryPanel } from './components/QueryPanel'

function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-4">
        <h1 className="text-xl font-semibold tracking-tight">Intellect</h1>
        <p className="text-sm text-slate-400">
          The data never moves. The intelligence does.
        </p>
      </header>
      <main className="grid gap-4 p-6 lg:grid-cols-3">
        <QueryPanel />
        <AgentActivityPanel />
        <AuditPanel />
      </main>
    </div>
  )
}

export default App
