import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Err, RunsOnBadge } from '../components'

const STORAGE_KEY = 'libra_conversations'

function loadConversations() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [] } catch { return [] }
}
function saveConversations(list) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
}

export default function Chat({ agents, hostedOnly = [], foundry }) {
  const [conversations, setConversations] = useState(loadConversations)
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [agent, setAgent] = useState('default')
  const [useRag, setUseRag] = useState(true)
  const [factCheck, setFactCheck] = useState(false)
  const [mode, setMode] = useState('local')
  const [topK, setTopK] = useState(3)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [recording, setRecording] = useState(false)
  const [speakingIdx, setSpeakingIdx] = useState(null)
  const endRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  // --- conversation history -------------------------------------------------
  function persist(id, msgs) {
    setConversations((prev) => {
      const existing = prev.find((c) => c.id === id)
      const title = msgs.find((m) => m.role === 'user')?.text?.slice(0, 40) || 'New conversation'
      const updated = existing
        ? prev.map((c) => (c.id === id ? { ...c, messages: msgs, title } : c))
        : [{ id, title, messages: msgs, createdAt: Date.now() }, ...prev]
      saveConversations(updated)
      return updated
    })
  }

  function newConversation() {
    const id = crypto.randomUUID()
    setActiveId(id)
    setMessages([])
  }

  function openConversation(id) {
    const conv = conversations.find((c) => c.id === id)
    if (conv) { setActiveId(id); setMessages(conv.messages) }
  }

  function deleteConversation(id) {
    const updated = conversations.filter((c) => c.id !== id)
    setConversations(updated)
    saveConversations(updated)
    if (activeId === id) { setActiveId(null); setMessages([]) }
  }

  // --- sending ---------------------------------------------------------------
  async function send() {
    const text = question.trim()
    if (!text || busy) return
    let id = activeId
    if (!id) { id = crypto.randomUUID(); setActiveId(id) }

    setQuestion(''); setError(null); setBusy(true)
    const withUser = [...messages, { role: 'user', text }]
    setMessages(withUser)
    try {
      const data = await api.ask({ question: text, use_rag: useRag, top_k: Number(topK),
                                  agent, agent_mode: mode, fact_check: factCheck })
      const withBot = [...withUser, { role: 'bot', data }]
      setMessages(withBot)
      persist(id, withBot)
    } catch (e) {
      const withErr = [...withUser, { role: 'err', text: e.message }]
      setMessages(withErr)
      persist(id, withErr)
      setError(e.message)
    } finally { setBusy(false) }
  }

  // --- microphone (speech-to-text) -------------------------------------------
  async function toggleRecording() {
    if (recording) {
      mediaRecorderRef.current?.stop()
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      audioChunksRef.current = []
      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data)
      recorder.onstop = async () => {
        setRecording(false)
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const file = new File([blob], 'recording.webm', { type: 'audio/webm' })
        try {
          setBusy(true)
          const result = await api.transcribe(file)
          setQuestion((q) => (q ? q + ' ' + result.text : result.text))
        } catch (e) {
          setError(`Transcription failed: ${e.message}`)
        } finally { setBusy(false) }
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch (e) {
      setError(`Microphone access denied: ${e.message}`)
    }
  }

  // --- speaker (text-to-speech) -----------------------------------------------
  async function playAnswer(idx, text) {
    try {
      setSpeakingIdx(idx)
      const blob = await api.speak({ text })
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.onended = () => setSpeakingIdx(null)
      audio.play()
    } catch (e) {
      setError(`Speech synthesis failed: ${e.message}`)
      setSpeakingIdx(null)
    }
  }

  const all = [...agents, ...hostedOnly]
  const current = all.find((a) => a.name === agent)

  const foundryReachable = foundry?.available
  const isHosted = current?.runs_on === 'both' || current?.runs_on === 'foundry'
  const localImpossible = current?.runs_on === 'foundry'
  const foundryBlocked =
    foundryReachable === false ||
    (foundryReachable === true && !isHosted)
  const foundryWhy =
    foundryReachable === false
      ? (foundry?.reason || 'The Agent Service cannot be reached from here.')
      : 'Not deployed to Foundry — deploy it from the Agents view'

  useEffect(() => {
    if (foundryBlocked && mode === 'foundry') setMode('local')
    else if (localImpossible && mode !== 'foundry') setMode('foundry')
  }, [agent, localImpossible, foundryBlocked])   // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="chat-layout">
      <aside className="chat-history">
        <button className="btn btn-primary btn-sm" style={{ width: '100%', marginBottom: '.6rem' }}
                onClick={newConversation}>
          + New conversation
        </button>
        {conversations.length === 0 && <p className="muted" style={{ fontSize: '.85rem' }}>No conversations yet</p>}
        {conversations.map((c) => (
          <div key={c.id} className={`history-item ${activeId === c.id ? 'active' : ''}`}>
            <button className="history-title" onClick={() => openConversation(c.id)}>
              {c.title || 'Conversation'}
            </button>
            <button className="history-delete" onClick={() => deleteConversation(c.id)} title="Delete">✕</button>
          </div>
        ))}
      </aside>

      <div className="chat-wrap">
        <div className="chat-bar">
          <select value={agent} onChange={(e) => setAgent(e.target.value)} title="Which persona answers">
            {agents.map((a) => <option key={a.name} value={a.name}>{a.display_name}</option>)}
            {hostedOnly.length > 0 && (
              <optgroup label="hosted in Foundry only">
                {hostedOnly.map((a) => <option key={a.name} value={a.name}>{a.display_name}</option>)}
              </optgroup>
            )}
          </select>
          {current && <RunsOnBadge runsOn={current.runs_on} reason={foundry?.reason} />}
          <label className="check" style={{ margin: 0 }} title="Retrieve from your documents and ground the answer">
            <input type="checkbox" checked={useRag} onChange={(e) => setUseRag(e.target.checked)} />
            use RAG
          </label>
          <label className="check" style={{ margin: 0 }}
                 title="After answering, verify the answer against the open web and attach a verdict">
            <input type="checkbox" checked={factCheck} onChange={(e) => setFactCheck(e.target.checked)} />
            fact-check
          </label>
          <select value={mode} onChange={(e) => setMode(e.target.value)} style={{ minWidth: '9rem' }}
                  title="Where the loop executes">
            <option value="local" disabled={localImpossible}
                    title={localImpossible ? 'This agent has no local JSON file' : ''}>
              local agent
            </option>
            <option value="foundry" disabled={foundryBlocked} title={foundryBlocked ? foundryWhy : ''}>
              Foundry agent{foundryReachable === false ? ' — no identity'
                            : foundryBlocked ? ' — not deployed' : ''}
            </option>
          </select>
          <input type="number" min="1" max="10" value={topK} onChange={(e) => setTopK(e.target.value)}
                 style={{ width: '4.5rem', flex: '0 0 auto' }} title="Passages to retrieve" />
          {foundryReachable === false && (
            <span className="badge muted" title={foundryWhy}>
              hosted agents off — key auth
            </span>
          )}
          <button className="btn btn-outline btn-sm" onClick={() => setMessages([])}>clear</button>
          {current && <span className="badge muted" title={current.description}>temp {current.temperature ?? '—'}</span>}
        </div>

        <div className="msgs">
          {messages.length === 0 && (
            <div className="card" style={{ alignSelf: 'center', maxWidth: '46rem', textAlign: 'center' }}>
              <h3>Suzy</h3>
              <p className="muted" style={{ margin: 0 }}>
                Ask a question about loans, mortgages or credit cards. Switch the persona to change how
                it answers, or turn RAG off to see the model answer without grounding.
              </p>
            </div>
          )}

          {messages.map((m, i) => {
            if (m.role === 'user') return <div className="msg user" key={i}>{m.text}</div>
            if (m.role === 'err') return <div className="msg err" key={i}><strong>Request failed:</strong> {m.text}</div>
            const d = m.data
            return (
              <div className="msg bot" key={i}>
                {d.answer}
                <div className="msg-meta">
                  <span className="badge">{d.agent?.display_name || 'agent'}</span>
                  <span className={`badge ${d.augmented ? 'gold' : 'muted'}`}>{d.augmented ? 'grounded' : 'no retrieval'}</span>
                  <span className="badge muted">{d.agent?.mode}</span>
                  <span className="badge muted">{d.model}</span>
                  {d.usage && <span className="badge muted">{d.usage.prompt_tokens}↑ {d.usage.completion_tokens}↓ tokens</span>}
                  <button className="btn btn-outline btn-sm" onClick={() => playAnswer(i, d.answer)}
                          disabled={speakingIdx === i} title="Listen to this answer">
                    {speakingIdx === i ? '🔊…' : '🔊 listen'}
                  </button>
                </div>
                {d.fact_check && (
                  <div className="src" style={{ marginTop: '.55rem',
                       borderLeftColor: d.fact_check.verdict === 'supported' ? 'var(--c-teal)'
                         : d.fact_check.verdict === 'contradicted' ? 'var(--c-crimson)' : 'var(--c-gold)' }}>
                    <span className={`badge ${d.fact_check.verdict === 'contradicted' ? 'crimson'
                      : d.fact_check.verdict === 'supported' ? '' : 'gold'}`}>
                      fact-check: {d.fact_check.verdict}
                    </span>{' '}
                    <span className="faint">{d.fact_check.confidence} confidence · {d.fact_check.evidence_from}</span>
                    {d.fact_check.error
                      ? <div className="faint" style={{ marginTop: '.3rem' }}>{d.fact_check.error}</div>
                      : <div style={{ marginTop: '.3rem' }}>{d.fact_check.reasoning}</div>}
                    {d.fact_check.sources?.length > 0 && (
                      <ul className="faint" style={{ margin: '.35rem 0 0', paddingLeft: '1.1rem' }}>
                        {d.fact_check.sources.map((sc) => (
                          <li key={sc.rank}>
                            <a href={sc.url} target="_blank" rel="noreferrer">{sc.title || sc.url}</a>
                            {' '}{sc.used ? `(${sc.chars_read} chars read)` : '(could not be read)'}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
                {d.retrieved?.length > 0 && (
                  <details className="sources">
                    <summary>{d.retrieved.length} retrieved passage{d.retrieved.length > 1 ? 's' : ''}</summary>
                    {d.retrieved.map((h, j) => (
                      <div className="src" key={h.id}>
                        <span className="score">[{j + 1}] score {h.score.toFixed(4)}</span>
                        <div>{h.text}</div>
                      </div>
                    ))}
                  </details>
                )}
                <details className="sources">
                  <summary>the exact prompt that was sent</summary>
                  <pre className="out" style={{ marginTop: '.4rem' }}>{`SYSTEM:\n${d.system_prompt}\n\nUSER:\n${d.prompt_sent}`}</pre>
                </details>
              </div>
            )
          })}
          {busy && <div className="msg bot"><span className="spin" /> thinking…</div>}
          <div ref={endRef} />
        </div>

        <Err error={error} />
        <div className="composer">
          <button className={`btn btn-outline ${recording ? 'recording' : ''}`} onClick={toggleRecording}
                  title={recording ? 'Stop recording' : 'Record a question'}>
            {recording ? '⏹' : '🎤'}
          </button>
          <textarea value={question} placeholder="Ask Suzy…  (Enter to send, Shift+Enter for a new line)"
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
          <button className="btn btn-primary" onClick={send} disabled={busy || !question.trim()}>Send</button>
        </div>
      </div>
    </div>
  )
}