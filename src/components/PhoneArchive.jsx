import { useEffect, useRef, useState } from 'react';
import { useProject } from '../context/ProjectContext.jsx';
import { useNavigation } from '../context/NavigationContext.jsx';
import './PhoneArchive.css';

export async function bridgeRequest(path, body) {
  const headers = {};
  if (body !== undefined) {
    const status = await fetch('/bridge/status').then(r => r.json());
    if (!status.token) throw new Error(status.error || 'Bridge unavailable');
    headers['X-Case-Token'] = status.token;
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(path, { method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

export default function PhoneArchive() {
  const { project, updateProject } = useProject();
  const { navigateToIdentifier } = useNavigation();
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState('');
  const [scope, setScope] = useState('');
  const [showAutomated, setShowAutomated] = useState(false);
  const [result, setResult] = useState({ rows: [], total: 0 });
  const [offset, setOffset] = useState(0);
  const [record, setRecord] = useState(null);
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const audio = useRef(null);
  useEffect(() => {
    let live = true;
    const refresh = () => bridgeRequest('/bridge/status').then(s => { if (live) setStatus(s.backend); }).catch(e => { if (live) setMessage(e.message); });
    refresh(); const timer = setInterval(refresh, 5000);
    return () => { live = false; clearInterval(timer); };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({q: query, kind: scope ? 'audio' : kind, limit: '50', offset: String(offset)});
        if (scope === 'shortlist') params.set('shortlist', '1');
        if (scope === 'ready') params.set('ready', '1');
        if (showAutomated) params.set('show_automated', '1');
        const res = await fetch(`/api/records?${params}`, { signal: controller.signal });
        const data = await res.json(); if (!res.ok) throw new Error(data.error);
        setResult(data);
      } catch(e) { if (e.name !== 'AbortError') setMessage(e.message); }
    }, 200);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, kind, offset, scope, showAutomated]);
  async function act(work) {
    setBusy(true); setMessage('');
    try { await work(); } catch(e) { setMessage(e.message); } finally { setBusy(false); }
  }
  async function inspect(id) {
    await act(async () => { setRecord(await bridgeRequest(`/api/record/${id}`)); });
  }
  async function add(ids) {
    await act(async () => {
      const incoming = await bridgeRequest('/bridge/case?ids=' + ids.join(','));
      updateProject(current => {
        const next = { ...current };
        for (const key of ['identifiers', 'connections', 'evidence', 'events']) {
          const existing = new Set((current[key] || []).map(x => x.id));
          const fresh = incoming[key].filter(x => !existing.has(x.id));
          if (key === 'identifiers') fresh.forEach((n, i) => { n.position = { x: (i % 5) * 350, y: (Math.ceil(current.identifiers.length / 5) + Math.floor(i / 5)) * 210 }; });
          next[key] = [...(current[key] || []), ...fresh];
        }
        return next;
      });
      setMessage('Added source records and their metadata links. Existing board edits remain intact.');
    });
  }
  async function process(action) {
    await act(async () => {
      await bridgeRequest('/api/process', {action});
      const s = await bridgeRequest('/bridge/status'); setStatus(s.backend);
      setMessage(action === 'pause' ? 'Processing paused.' : 'Started the existing text-led queue.');
    });
  }
  return <section className="phone-archive">
    <header className="phone-tools">
      <h2>Phone archive</h2>
      <p>{status?.total?.toLocaleString() || '…'} indexed records · {status?.shortlist_ready ?? '…'}/{status?.shortlist_total ?? '…'} shortlist transcripts ready</p>
      <p>Jev 1.14 · Deepgram Nova-3 · Key {status?.key_set ? 'connected' : 'unavailable'} · Spend ${status?.spent?.toFixed(4) ?? '…'} / ${status?.budget ?? '…'}</p>
      <div className="phone-actions">
        <button className="btn" disabled={busy} onClick={() => process(status?.paused ? 'start' : 'pause')}>{status?.paused ? 'Process text-led shortlist' : 'Pause processing'}</button>
        <button className="btn" disabled={busy} onClick={() => act(async () => { await bridgeRequest('/bridge/save', project); setMessage('Saved the board locally.'); })}>Save board locally</button>
        <a className="btn" href="/bridge/case?all=1" download="phone-archive.case.json">Export full archive</a>
      </div>
      <p role="status">{message || 'The board saves locally. Tags and time proximity suggest review; they do not prove shared meaning.'}</p>
    </header>
    <div className="phone-columns">
      <div className="phone-results">
        <form onSubmit={e => e.preventDefault()} className="phone-search">
          <label>Search texts, transcripts, contacts<input value={query} onChange={e => {setQuery(e.target.value);setOffset(0);}} type="search" /></label>
          <label>Scope<select value={scope} onChange={e => {setScope(e.target.value);setOffset(0);}}><option value="">Archive</option><option value="shortlist">Text-led shortlist</option><option value="ready">Ready transcripts</option></select></label>
          <label>Record type<select disabled={!!scope} value={kind} onChange={e => {setKind(e.target.value);setOffset(0);}}><option value="">All types</option><option value="text">Texts</option><option value="audio">Audio</option><option value="call">Calls</option></select></label>
        <label><span><input type="checkbox" checked={showAutomated} onChange={e => {setShowAutomated(e.target.checked);setOffset(0);}} /> Show automated texts</span></label>
        </form>
        <div className="phone-actions"><span>{result.total.toLocaleString()} matches</span><button className="btn" disabled={busy || !result.rows.length} onClick={() => add(result.rows.map(r => r.id))}>Map these results</button></div>
        <ul>{result.rows.map(r => <li key={r.id}><button className="phone-result" onClick={() => inspect(r.id)} aria-pressed={record?.id === r.id}><strong>{r.title}</strong><small>{r.kind} · {r.at} · {r.transcription === 'done' ? 'Transcript ready' : r.person}</small><span>{r.body?.slice(0, 180)}</span></button></li>)}</ul>
        <div className="phone-actions"><button className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0,offset-50))}>Previous</button><span>{result.total ? offset+1 : 0}–{Math.min(offset+50,result.total)}</span><button className="btn" disabled={offset+50 >= result.total} onClick={() => setOffset(offset+50)}>Next</button></div>
      </div>
      <article className="phone-detail">{record ? <>
        <h3>{record.title}</h3><p>{record.kind} · {record.at} · Record {record.id}</p>
        <div className="phone-actions"><button className="btn" disabled={busy} onClick={() => add([record.id])}>Add to map</button>{project.identifiers.some(n => n.id === `record-${record.id}`) && <button className="btn" onClick={() => navigateToIdentifier(`record-${record.id}`)}>Find on map</button>}<a href={`/source/${record.id}`} target="_blank" rel="noreferrer">Open source</a></div>
        {record.kind === 'audio' && <audio key={record.id} ref={audio} controls preload="metadata" src={`/api/media/${record.id}`} />}
        <p>{record.tags.map(t => t.tag).join(' · ') || 'No tags'}</p>
        <pre>{record.body || 'No transcript text available.'}</pre>
        {record.metadata?.segments?.map((s,i) => <p key={i}><button className="btn btn-sm" onClick={() => {if(audio.current){audio.current.currentTime=s.start;audio.current.play().catch(e=>setMessage(e.message));}}}>{Math.round(s.start)}s</button> {s.text}</p>)}
        <h4>Linked source records</h4>{record.related.map(r => <p key={r.id}><button className="btn" onClick={() => inspect(r.id)}>{r.title}</button><small>{r.reasons.join(' · ')}</small></p>)}
        <h4>Original reference</h4><pre>{record.phone_path || record.path}\n{record.source_key}\n{record.sha256}</pre>
      </> : <p>Select a source record to read its text, play audio, and inspect its links.</p>}</article>
    </div>
  </section>;
}
