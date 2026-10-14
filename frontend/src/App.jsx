import { useCallback, useEffect, useRef, useState } from 'react'
import { Activity, Check, CircleHelp, Clock3, FileImage, Leaf, LoaderCircle, MessageCircle, Plus, Send, ShieldAlert, Sprout, Upload, X } from 'lucide-react'

const SESSION_KEY = 'verdant.session.v1'
const sessionId = (() => {
  let current = localStorage.getItem(SESSION_KEY)
  if (!current) { current = crypto.randomUUID(); localStorage.setItem(SESSION_KEY, current) }
  return current
})()

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'X-Session-Id': sessionId, ...(options.headers || {}) } })
  const data = response.headers.get('content-type')?.includes('application/json') ? await response.json() : null
  if (!response.ok) throw new Error(data?.error || data?.detail || 'Something went wrong. Please try again.')
  return data
}

function prettyDisease(value = '') {
  return value.replaceAll('___', ' · ').replaceAll('_', ' ').replace(/\(([^)]+)\)/g, '($1)').trim()
}

function App() {
  const [history, setHistory] = useState([])
  const [current, setCurrent] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [backend, setBackend] = useState('checking')
  const [dragOver, setDragOver] = useState(false)
  const [showAbout, setShowAbout] = useState(false)
  const fileInput = useRef(null)

  const refreshHistory = useCallback(async () => {
    const rows = await api('/api/diagnoses')
    setHistory(rows)
  }, [])

  useEffect(() => {
    Promise.all([api('/api/health'), refreshHistory()])
      .then(() => setBackend('online'))
      .catch(() => { setBackend('offline'); setError('Backend unavailable. Start the application stack and try again.') })
      .finally(() => setLoadingHistory(false))
  }, [refreshHistory])

  async function openDiagnosis(id) {
    setError('')
    try { setCurrent(await api(`/api/diagnoses/${id}`)) }
    catch (err) { setError(err.message) }
  }

  async function upload(file) {
    if (!file) return
    setError('')
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setError('Choose a JPEG, PNG, or WebP image.'); return
    }
    if (file.size > 15 * 1024 * 1024) { setError('Images must be 15 MB or smaller.'); return }
    setUploading(true)
    const form = new FormData()
    form.append('image', file)
    try {
      const diagnosis = await api('/api/diagnoses', { method: 'POST', body: form })
      setCurrent(diagnosis)
      await refreshHistory()
    } catch (err) { setError(err.message) }
    finally { setUploading(false); if (fileInput.current) fileInput.current.value = '' }
  }

  async function sendMessage(message) {
    if (!current || !message.trim() || sending) return
    setError(''); setSending(true)
    try {
      await api(`/api/diagnoses/${current.id}/messages`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message.trim() }),
      })
      await openDiagnosis(current.id)
    } catch (err) { setError(err.message) }
    finally { setSending(false) }
  }

  const createNew = () => { setCurrent(null); setError(''); fileInput.current?.click() }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-icon"><Sprout size={21} /></span><span>verdant<span className="brand-dot">.</span></span></div>
      <button className="new-button" onClick={createNew}><Plus size={17} /> New diagnosis</button>
      <div className="history-heading"><span>YOUR DIAGNOSES</span><span className="history-count">{history.length}</span></div>
      <div className="history-list">
        {loadingHistory ? <div className="history-loading"><LoaderCircle className="spin" size={15} /> Loading history</div> : history.length ? history.map(item =>
          <button className={`history-item ${current?.id === item.id ? 'active' : ''}`} key={item.id} onClick={() => openDiagnosis(item.id)}>
            <img src={item.imageUrl} alt="" className="history-thumb" />
            <span className="history-copy"><strong>{prettyDisease(item.diseaseClass).split(' · ').at(-1)}</strong><small><Clock3 size={11} /> {dateLabel(item.createdAt)}</small></span>
            {current?.id === item.id && <span className="active-mark" />}
          </button>) : <p className="empty-history">Your diagnosis threads will appear here.</p>}
      </div>
      <div className="sidebar-bottom">
        <div className={`service-status ${backend}`}><span className="status-dot" />{backend === 'online' ? 'AI service ready' : backend === 'checking' ? 'Connecting…' : 'Service unavailable'}</div>
        <p>History stays in this browser on this device.</p>
      </div>
    </aside>

    <main className="main-panel">
      <header className="topbar">
        <div className="mobile-brand"><Sprout size={19} /> verdant<span>.</span></div>
        <div className="topbar-label"><span className="topbar-pulse" /> PLANT HEALTH ASSISTANT</div>
        <button className="help-link" title="How results are produced" onClick={() => setShowAbout(true)}><CircleHelp size={17} /><span>About results</span></button>
      </header>

      {error && <div className="error-banner"><ShieldAlert size={17} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss"><X size={15} /></button></div>}

      {!current ? <section className="welcome-view">
        <div className="welcome-copy"><div className="eyebrow"><span /> GROUNDED PLANT CARE</div>
          <h1>A clearer picture<br />of <em>plant health.</em></h1>
          <p>Upload a leaf photo for a disease prediction and guidance grounded in agricultural references. Each photo starts its own conversation.</p>
        </div>
        <div className={`upload-card ${dragOver ? 'dragging' : ''}`} onDragOver={e => { e.preventDefault(); setDragOver(true) }} onDragLeave={() => setDragOver(false)} onDrop={e => { e.preventDefault(); setDragOver(false); upload(e.dataTransfer.files?.[0]) }}>
          <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={e => upload(e.target.files?.[0])} />
          <div className="upload-icon">{uploading ? <LoaderCircle className="spin" size={24} /> : <FileImage size={25} />}</div>
          <h2>{uploading ? 'Reading your image…' : 'Start with a leaf photo'}</h2>
          <p>{uploading ? 'The image is being classified and checked against verified references.' : 'A clear, well-lit photo of one leaf works best.'}</p>
          <button className="upload-button" onClick={() => fileInput.current?.click()} disabled={uploading}><Upload size={16} /> {uploading ? 'Analyzing image' : 'Choose an image'}</button>
          <span className="upload-footnote">JPEG, PNG or WebP · up to 15 MB</span>
          <span className="drop-hint">or drop an image here</span>
        </div>
        <div className="welcome-note"><ShieldAlert size={15} /><span>Predictions are trained on controlled PlantVillage images. Field results can differ, and every prediction should be checked against what you observe.</span></div>
      </section> : <DiagnosisThread diagnosis={current} sending={sending} onSend={sendMessage} onNew={createNew} />}
    </main>
    {showAbout && <div className="modal-backdrop" onClick={() => setShowAbout(false)}><section className="about-modal" role="dialog" aria-modal="true" aria-labelledby="about-title" onClick={e => e.stopPropagation()}><button className="modal-close" onClick={() => setShowAbout(false)} aria-label="Close"><X size={17} /></button><div className="about-icon"><Sprout size={20} /></div><div className="eyebrow"><span /> HOW RESULTS WORK</div><h2 id="about-title">A useful guide, not a final diagnosis.</h2><p>The image model always chooses one of its 38 PlantVillage classes. Below 70% confidence, Verdant flags the prediction as uncertain. Even a higher score does not guarantee that a field photo is correctly classified.</p><p>The model was evaluated on controlled PlantVillage images, so real field performance may be lower. Advisory answers cite only retrieved reference documents. When no verified reference covers a class, Verdant will say so rather than fill the gap with unsupported treatment advice.</p><button className="modal-done" onClick={() => setShowAbout(false)}>Got it</button></section></div>}
  </div>
}

function DiagnosisThread({ diagnosis, sending, onSend, onNew }) {
  const [message, setMessage] = useState('')
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [diagnosis.messages?.length, sending])
  const confidencePercent = Math.round((diagnosis.confidence || 0) * 100)
  const lowConfidence = diagnosis.confidence < 0.70
  const noReference = diagnosis.retrievalStatus === 'no_verified_reference' || diagnosis.retrievalStatus === 'no_reference_document' || diagnosis.retrievalStatus === 'below_similarity_threshold'
  const submit = e => { e.preventDefault(); const value = message; setMessage(''); onSend(value) }

  return <section className="thread-view">
    <div className="thread-header"><div><div className="eyebrow"><span /> DIAGNOSIS THREAD</div><h1>{prettyDisease(diagnosis.diseaseClass)}</h1><p>Started {dateLabel(diagnosis.createdAt, true)}</p></div><button className="new-thread-button" onClick={onNew}><Plus size={15} /> New photo</button></div>
    <div className="thread-scroll">
      <article className="diagnosis-card">
        <div className="diagnosis-photo-wrap"><img src={diagnosis.imageUrl} alt="Uploaded leaf for diagnosis" className="diagnosis-photo" /><span className="photo-tag"><Leaf size={12} /> Uploaded leaf</span></div>
        <div className="diagnosis-detail">
          <div className="result-kicker"><Check size={14} /> MODEL PREDICTION</div>
          <h2>{prettyDisease(diagnosis.diseaseClass)}</h2>
          <div className="confidence-line"><span>Model confidence</span><strong>{confidencePercent}%</strong></div>
          <div className="confidence-track"><span style={{ width: `${confidencePercent}%` }} /></div>
          {lowConfidence && <div className="confidence-warning"><ShieldAlert size={16} /><p><strong>Low confidence — treat this as uncertain.</strong> The model always selects one of its 38 trained classes, so unfamiliar plants, non-leaf photos, or field conditions can lead to a misleading label. Try a clearer leaf photo or ask a local agricultural expert.</p></div>}
          <div className="lab-note"><Activity size={15} /><span>Test accuracy was measured on controlled PlantVillage images. Field performance may be lower.</span></div>
        </div>
      </article>

      <div className="message-stream">
        {diagnosis.messages?.map((item, index) => item.sender === 'assistant' ? <div className="assistant-message" key={`${item.timestamp}-${index}`}>
          <div className="assistant-avatar"><Sprout size={16} /></div><div className="message-body">
            {index === 0 && <div className="message-label">GROUNDED ADVISORY</div>}
            {index === 0 && noReference && <div className="coverage-notice"><ShieldAlert size={16} /><span><strong>No verified reference available</strong><br />The knowledge base does not contain a confirmed source for this class. The guidance below explains this limitation.</span></div>}
            <p className="assistant-text">{item.message}</p>
            {index === 0 && diagnosis.sources?.length > 0 && <SourceList sources={diagnosis.sources} />}
          </div>
        </div> : <div className="user-message" key={`${item.timestamp}-${index}`}><span>{item.message}</span></div>)}
        {sending && <div className="assistant-message"><div className="assistant-avatar"><Sprout size={16} /></div><div className="typing-indicator"><i /><i /><i /></div></div>}
        <div ref={endRef} />
      </div>
    </div>
    <div className="composer-wrap">
      <form className="composer" onSubmit={submit}><textarea value={message} onChange={e => setMessage(e.target.value)} placeholder={noReference ? 'Ask about this diagnosis…' : 'Ask a follow-up about this diagnosis…'} rows={1} maxLength={4000} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(e) } }} disabled={sending} /><button type="submit" disabled={sending || !message.trim()} aria-label="Send follow-up"><Send size={17} /></button></form>
      <div className="composer-caption"><span><MessageCircle size={12} /> This thread stays with this diagnosis</span><span>Enter to send · Shift + Enter for a new line</span></div>
    </div>
  </section>
}

function SourceList({ sources }) {
  return <div className="sources"><div className="sources-title">VERIFIED SOURCES USED</div>{sources.map(source => <div className="source-chip" key={source.chunk_id}><span className="source-dot" /><span>{source.source_file?.replaceAll('_', ' ').replace(/\.pdf$/i, '')}</span><small>{source.chunk_id}</small></div>)}</div>
}

function dateLabel(value, includeTime = false) {
  if (!value) return 'just now'
  const date = new Date(value)
  const today = new Date()
  if (date.toDateString() === today.toDateString()) return includeTime ? `today at ${date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}` : date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  return date.toLocaleDateString([], { month: 'short', day: 'numeric', ...(includeTime ? { year: 'numeric' } : {}) })
}

export default App
