import { useContext, useEffect, useState } from 'react';
import api from '../api/api';
import AppContext from '../store/AppContext';
import VaultGate from '../components/VaultGate';

const VAULT_PRESETS = {
  company: [
    'How many venues does Pulse support?',
    'What was the close on 2024-03-15 09:30?',
    'Who is the CTO of Acme Analytics?',
    'What is the secret internal codeword?',
  ],
  organization: [
    'What is step 3 of the work plan?',
    'What does contingency procedure C-7 (Quokka) do?',
    'Who wrote the contingency procedures?',
    'What is the internal reference code for Lunar Harbor artifacts?',
  ],
  personal: [
    'What am I allergic to?',
    'What is my morning coffee recipe?',
    'What are my 2026 professional goals?',
    'Who is my lawyer and what do they do?',
  ],
  relativity: [
    'What is the lab identifier for this vault?',
    'Summarize the working model for the Hubble tension',
    'What is the codename for the ringdown extraction method?',
    'Which papers are marked as required reading?',
  ],
  'saas-ai': [
    'What is the gross-margin staircase framework?',
    'Which moats does SmartBaseAI target?',
    'What are the steps in the pricing playbook?',
    'What are the anti-patterns for AI SaaS pricing?',
  ],
  'smartbase-docs': [
    'How does a super_admin pick a vault?',
    'What does the RAG Visualizer show me?',
    'What is the most valuable thing this product delivers to a company?',
    'How is data isolated between tenants?',
  ],
};

const FALLBACK_PRESETS = [
  'What is in this vault?',
  'Summarize the main topics.',
  'Who are the key people mentioned?',
];

function StageCard({ title, subtitle, tone = 'slate', active = true, children }) {
  const toneMap = {
    slate: 'border-slate-300 bg-white',
    indigo: 'border-indigo-300 bg-indigo-50',
    emerald: 'border-emerald-300 bg-emerald-50',
    amber: 'border-amber-300 bg-amber-50',
    rose: 'border-rose-300 bg-rose-50',
    violet: 'border-violet-300 bg-violet-50',
  };
  const headerTone = {
    slate: 'text-slate-700',
    indigo: 'text-indigo-700',
    emerald: 'text-emerald-700',
    amber: 'text-amber-700',
    rose: 'text-rose-700',
    violet: 'text-violet-700',
  };
  return (
    <div
      className={`rounded-lg border-2 shadow-sm transition-all ${toneMap[tone]} ${
        active ? 'opacity-100' : 'opacity-50'
      }`}
    >
      <div className={`px-3 py-2 border-b border-current/10 ${headerTone[tone]}`}>
        <div className="text-xs font-bold uppercase tracking-wide">{title}</div>
        {subtitle && <div className="text-[11px] text-slate-500">{subtitle}</div>}
      </div>
      <div className="p-3 text-xs text-slate-700">{children}</div>
    </div>
  );
}

function Arrow({ label, vertical = false }) {
  if (vertical) {
    return (
      <div className="flex flex-col items-center text-slate-400">
        <div className="w-px h-4 bg-slate-400"></div>
        {label && <div className="text-[10px] my-1">{label}</div>}
        <div className="w-0 h-0 border-l-4 border-l-transparent border-r-4 border-r-transparent border-t-[6px] border-t-slate-400"></div>
      </div>
    );
  }
  return (
    <div className="flex items-center text-slate-400 px-1">
      {label && <div className="text-[10px] mr-1 whitespace-nowrap">{label}</div>}
      <div className="h-px w-6 bg-slate-400"></div>
      <div className="w-0 h-0 border-t-4 border-t-transparent border-b-4 border-b-transparent border-l-[6px] border-l-slate-400"></div>
    </div>
  );
}

/**
 * Scale a Chroma L2 distance into a 0..1 "relevance" score for the bar.
 * Chroma's sentence-transformer distances are ~0 (identical) to ~2 (opposite).
 * We clip to [0, 2] and invert so strong matches render as long green bars.
 */
function relevanceFromDistance(d) {
  if (d == null) return null;
  const clipped = Math.max(0, Math.min(2, d));
  return 1 - clipped / 2;
}

function ScoreBar({ distance, kept }) {
  const rel = relevanceFromDistance(distance);
  if (rel == null) {
    return (
      <div className="flex items-center gap-2">
        <div className="h-2 w-32 rounded bg-amber-200"></div>
        <span className="text-[10px] text-amber-700 font-mono">keyword</span>
      </div>
    );
  }
  const pct = Math.round(rel * 100);
  const color =
    rel >= 0.6 ? 'bg-emerald-500' : rel >= 0.4 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="flex items-center gap-2">
      <div className="relative h-2 w-32 rounded bg-slate-200 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }}></div>
      </div>
      <span className="text-[10px] text-slate-600 font-mono min-w-[90px]">
        d={distance.toFixed(3)} · rel={pct}%
      </span>
      {kept && (
        <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-100 text-emerald-700 border border-emerald-300">
          kept
        </span>
      )}
    </div>
  );
}

function DocChip({ entry, index }) {
  const file = entry.metadata?.filename || '(unknown)';
  const score = entry.score != null ? entry.score.toFixed(3) : '—';
  const sourceBadge =
    entry.source === 'keyword'
      ? 'bg-amber-100 text-amber-800 border-amber-300'
      : 'bg-violet-100 text-violet-800 border-violet-300';
  return (
    <div className="border rounded-md bg-white p-2 mb-2">
      <div className="flex items-center justify-between mb-1">
        <span className={`text-[10px] px-1.5 py-0.5 rounded border ${sourceBadge}`}>
          {entry.source}
        </span>
        <span className="text-[10px] text-slate-500 font-mono">
          #{index + 1} · dist {score}
        </span>
      </div>
      <div className="text-[11px] font-semibold text-slate-700 truncate">{file}</div>
      <div className="text-[11px] text-slate-500 mt-1 line-clamp-3 whitespace-pre-wrap">
        {entry.document.slice(0, 240)}
        {entry.document.length > 240 ? '…' : ''}
      </div>
    </div>
  );
}

export default function RagVisualizer() {
  const { activeTenant } = useContext(AppContext);
  const role = localStorage.getItem('role');
  const username = localStorage.getItem('username') || '';
  const [query, setQuery] = useState('');
  const [trace, setTrace] = useState(null);
  const [traceIsSaved, setTraceIsSaved] = useState(false);
  const [currentSavedId, setCurrentSavedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [models, setModels] = useState([]);
  const [selectedModelIdx, setSelectedModelIdx] = useState(0);

  // Saved traces ------------------------------------------------------
  const [savedTraces, setSavedTraces] = useState([]);
  const [savedExpanded, setSavedExpanded] = useState(true);

  const loadSaved = async (tenant) => {
    if (!tenant) {
      setSavedTraces([]);
      return;
    }
    try {
      const res = await api.get('/chat/traces', { params: { tenant_id: tenant } });
      setSavedTraces(res.data?.traces || []);
    } catch {
      setSavedTraces([]);
    }
  };

  const saveCurrentTrace = async () => {
    if (!trace || !activeTenant) return;
    let title = prompt('Title for this saved trace:', trace.query?.slice(0, 80) || '');
    if (title === null) return; // cancelled
    title = title.trim() || trace.query?.slice(0, 80) || '';
    try {
      const res = await api.post('/chat/traces', {
        tenant_id: activeTenant,
        title,
        query: trace.query,
        reply: trace.reply,
        trace,
      });
      setTraceIsSaved(true);
      setCurrentSavedId(res.data?.id || null);
      await loadSaved(activeTenant);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'save failed');
    }
  };

  const loadSavedTrace = async (id) => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/chat/traces/${id}`);
      setTrace(res.data.trace);
      setQuery(res.data.query);
      setTraceIsSaved(true);
      setCurrentSavedId(res.data.id);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'load failed');
    } finally {
      setLoading(false);
    }
  };

  const deleteSavedTrace = async (id, e) => {
    e.stopPropagation();
    if (!confirm('Delete this saved trace?')) return;
    try {
      await api.delete(`/chat/traces/${id}`);
      if (id === currentSavedId) {
        setTraceIsSaved(false);
        setCurrentSavedId(null);
      }
      await loadSaved(activeTenant);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'delete failed');
    }
  };

  useEffect(() => {
    setTrace(null);
    setQuery('');
    setTraceIsSaved(false);
    setCurrentSavedId(null);
    if (!activeTenant) {
      setModels([]);
      setSavedTraces([]);
      return;
    }
    api
      .get(`/admin/tenants/${activeTenant}`)
      .then((res) => {
        const list = res.data?.models || [];
        setModels(list);
        setSelectedModelIdx(0);
      })
      .catch(() => setModels([]));
    loadSaved(activeTenant);
  }, [activeTenant]);

  const run = async (q) => {
    const message = (q ?? query).trim();
    if (!message || !activeTenant) return;
    setLoading(true);
    setError('');
    setTraceIsSaved(false);
    setCurrentSavedId(null);
    try {
      const chosen = models[selectedModelIdx];
      const body = {
        session_id: 'rag-visualizer',
        tenant_id: activeTenant.replace(/\s+/g, ''),
        message,
      };
      if (chosen) {
        body.model_provider = chosen.provider;
        body.model_name = chosen.name;
      }
      const res = await api.post('/chat/trace', body);
      setTrace(res.data);
      setQuery(message);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Trace failed');
      setTrace(null);
    } finally {
      setLoading(false);
    }
  };

  const formatWhen = (iso) => {
    if (!iso) return '';
    try {
      const d = new Date(iso + 'Z');
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return iso.slice(0, 16);
    }
  };

  if (!activeTenant) {
    return <VaultGate role={role} title="Pick a vault to run retrieval traces" />;
  }

  const presets = VAULT_PRESETS[activeTenant] || FALLBACK_PRESETS;

  const stages = trace?.stages;
  const dbActive = !!stages?.db_lookup?.matched;
  const ragCombined = stages?.rag_retrieval?.combined || [];
  const ragActive = ragCombined.length > 0;

  return (
      <div className="flex-1 overflow-y-auto bg-slate-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-slate-800">RAG Visualizer</h1>
            <p className="text-sm text-slate-600 mt-1">
              Watch a single query flow through the three-source orchestrator: conversation
              history, exact structured DB lookup, and hybrid (keyword ∪ semantic) retrieval
              over the tenant's vector store — then fusion, prompt assembly, and the LLM call.
            </p>
          </div>

          {/* Query bar */}
          <div className="bg-white rounded-lg border border-slate-200 p-4 mb-6 shadow-sm">
            <div className="flex gap-2">
              <input
                type="text"
                className="flex-1 px-3 py-2 border border-slate-300 rounded-md text-sm"
                placeholder={`Ask something about the ${activeTenant} vault…`}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') run();
                }}
              />
              {models.length > 0 && (
                <select
                  className="px-2 py-2 border border-slate-300 rounded-md text-sm min-w-[160px]"
                  value={selectedModelIdx}
                  onChange={(e) => setSelectedModelIdx(Number(e.target.value))}
                  title="Pick which LLM this trace uses"
                >
                  {models.map((m, i) => (
                    <option key={`${m.provider}:${m.name}`} value={i}>
                      {m.label || `${m.provider}/${m.name}`}
                    </option>
                  ))}
                </select>
              )}
              <button
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 text-white rounded-md text-sm font-medium"
                onClick={() => run()}
                disabled={loading}
              >
                {loading ? 'Tracing…' : 'Run trace'}
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {presets.map((q) => (
                <button
                  key={q}
                  className="text-xs px-2 py-1 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded"
                  onClick={() => run(q)}
                >
                  {q}
                </button>
              ))}
            </div>
            {error && (
              <div className="mt-3 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded p-2">
                {error}
              </div>
            )}

            {/* Saved traces — reload without spending tokens */}
            <div className="mt-4 pt-3 border-t border-slate-100">
              <button
                type="button"
                className="w-full flex items-center justify-between text-xs font-semibold text-slate-600 uppercase tracking-wide hover:text-slate-800"
                onClick={() => setSavedExpanded((v) => !v)}
              >
                <span className="flex items-center gap-2">
                  <span>{savedExpanded ? '▾' : '▸'}</span>
                  <span>Saved traces</span>
                  <span className="text-slate-400 font-normal normal-case">
                    ({savedTraces.length})
                  </span>
                </span>
                <span className="text-[10px] text-slate-400 font-normal normal-case">
                  click to reload without re-running the LLM
                </span>
              </button>
              {savedExpanded && (
                <div className="mt-2">
                  {savedTraces.length === 0 ? (
                    <div className="text-[11px] text-slate-400 italic">
                      No saved traces yet — run a query, then click "💾 Save trace" on the
                      pipeline diagram to capture it for reuse.
                    </div>
                  ) : (
                    <ul className="space-y-1 max-h-56 overflow-y-auto">
                      {savedTraces.map((t) => {
                        const isCurrent = t.id === currentSavedId;
                        return (
                          <li key={t.id}>
                            <button
                              className={`w-full text-left text-xs p-2 rounded border flex items-start gap-2 ${
                                isCurrent
                                  ? 'bg-indigo-50 border-indigo-300'
                                  : 'bg-white border-slate-200 hover:bg-slate-50'
                              }`}
                              onClick={() => loadSavedTrace(t.id)}
                            >
                              <span className="flex-shrink-0 text-indigo-500">💾</span>
                              <div className="flex-1 min-w-0">
                                <div className="font-semibold text-slate-800 truncate">
                                  {t.title}
                                </div>
                                <div className="text-[10px] text-slate-500 truncate">
                                  {t.query}
                                </div>
                                <div className="text-[10px] text-slate-400 mt-0.5">
                                  {t.created_by} · {formatWhen(t.created_at)}
                                  {t.reply_len
                                    ? ` · reply ${t.reply_len} chars`
                                    : ''}
                                </div>
                              </div>
                              {(role === 'super_admin' || t.created_by === username) && (
                                <button
                                  type="button"
                                  className="flex-shrink-0 text-slate-400 hover:text-rose-600 text-xs px-1"
                                  onClick={(e) => deleteSavedTrace(t.id, e)}
                                  title="Delete saved trace"
                                >
                                  ✕
                                </button>
                              )}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Pipeline */}
          {!trace && !loading && (
            <div className="text-center text-slate-500 py-20 border-2 border-dashed border-slate-300 rounded-lg bg-white">
              Run a trace above to visualize the pipeline.
            </div>
          )}

          {trace && (
            <>
              <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs text-slate-500">
                    {traceIsSaved ? (
                      <span className="text-emerald-700">
                        ✓ Saved trace #{currentSavedId}
                      </span>
                    ) : (
                      <span>Unsaved — click "Save trace" to keep this view.</span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="text-xs px-3 py-1 rounded border disabled:opacity-50 disabled:cursor-not-allowed
                      bg-indigo-50 hover:bg-indigo-100 border-indigo-200 text-indigo-800
                      disabled:bg-slate-50 disabled:text-slate-500 disabled:border-slate-200"
                    onClick={saveCurrentTrace}
                    disabled={traceIsSaved}
                  >
                    💾 Save trace
                  </button>
                </div>
                <div className="flex flex-col lg:flex-row lg:items-stretch lg:justify-center gap-3">
                  {/* Query */}
                  <StageCard title="1. User query" tone="slate">
                    <div className="italic text-slate-700">"{trace.query}"</div>
                    <div className="text-[10px] text-slate-400 mt-2">
                      tenant: {trace.tenant_id}
                    </div>
                  </StageCard>

                  <Arrow label="session" />

                  {/* Orchestrator (contains 3 sub-stages) */}
                  <div className="flex flex-col gap-2 lg:w-[420px]">
                    <div className="text-center text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      2. Orchestrator
                    </div>
                    <StageCard title="history" subtitle="ConversationManager" tone="slate" active={true}>
                      {stages.history.messages.length === 0 ? (
                        <span className="text-slate-400">(empty — fresh session)</span>
                      ) : (
                        <div className="space-y-1">
                          {stages.history.messages.slice(-3).map((m, i) => (
                            <div key={i} className="truncate">
                              <b>{m.role}:</b> {m.text}
                            </div>
                          ))}
                        </div>
                      )}
                    </StageCard>
                    <StageCard
                      title="DB exact lookup"
                      subtitle={`db/query_engine.exact_lookup${
                        stages.db_lookup.detected_date
                          ? ` → date=${stages.db_lookup.detected_date}`
                          : ''
                      }`}
                      tone="emerald"
                      active={dbActive}
                    >
                      {stages.db_lookup.detected_date == null ? (
                        <span className="text-slate-400">no date detected in query — skipped</span>
                      ) : dbActive ? (
                        <div>
                          <div className="font-mono text-[10px] text-emerald-900 bg-emerald-100 rounded p-2 overflow-x-auto">
                            {JSON.stringify(stages.db_lookup.row, null, 0)}
                          </div>
                          <div className="mt-2 text-slate-600">{stages.db_lookup.text}</div>
                        </div>
                      ) : (
                        <span className="text-slate-400">date detected but no row matched</span>
                      )}
                    </StageCard>
                    <StageCard
                      title="Hybrid retrieval"
                      subtitle={
                        stages.rag_retrieval.store
                          ? `Chroma · ${stages.rag_retrieval.store.count ?? '?'} vectors`
                          : 'keyword ∪ semantic'
                      }
                      tone="violet"
                      active={ragActive}
                    >
                      {stages.rag_retrieval.store && (
                        <div className="text-[10px] text-slate-500 mb-2 font-mono break-all">
                          {stages.rag_retrieval.store.embedding_model || 'embedding fn'}
                          {stages.rag_retrieval.store.embedding_dim
                            ? ` · ${stages.rag_retrieval.store.embedding_dim}-d`
                            : ''}
                          {stages.rag_retrieval.store.device
                            ? ` · ${stages.rag_retrieval.store.device}`
                            : ''}
                        </div>
                      )}
                      {ragCombined.length === 0 ? (
                        <span className="text-slate-400">no documents retrieved</span>
                      ) : (
                        ragCombined.map((e, i) => <DocChip key={i} entry={e} index={i} />)
                      )}
                      <div className="text-[10px] text-slate-400 mt-1">
                        keyword: {stages.rag_retrieval.keyword?.length || 0} · semantic:{' '}
                        {stages.rag_retrieval.semantic?.length || 0} · kept:{' '}
                        {ragCombined.length}
                      </div>
                    </StageCard>
                  </div>

                  <Arrow label="merge" />

                  {/* Fusion */}
                  <StageCard
                    title="3. Fusion"
                    subtitle="DB-preferred · RAG supplemental"
                    tone="amber"
                    active={!!stages.fusion.merged}
                  >
                    {!stages.fusion.merged ? (
                      <span className="text-slate-400">
                        both sources empty → "No information"
                      </span>
                    ) : (
                      <pre className="whitespace-pre-wrap text-[10px] bg-amber-100 rounded p-2 max-h-48 overflow-y-auto">
                        {stages.fusion.merged}
                      </pre>
                    )}
                  </StageCard>

                  <Arrow label="prompt" />

                  {/* LLM */}
                  <StageCard
                    title="4. LLM"
                    subtitle={stages.llm.model_type}
                    tone="rose"
                    active={!!stages.llm.reply}
                  >
                    <div className="text-[10px] text-slate-500 mb-1">model:</div>
                    <div className="text-[11px] font-mono text-rose-700 mb-2">
                      {stages.llm.model_type}
                    </div>
                    <div className="text-[10px] text-slate-500 mb-1">reply:</div>
                    <pre className="whitespace-pre-wrap text-[11px] bg-rose-100 rounded p-2 max-h-48 overflow-y-auto">
                      {stages.llm.reply}
                    </pre>
                  </StageCard>
                </div>
              </div>

              {/* Vector store deep dive */}
              {stages.rag_retrieval.store && (
                <div className="bg-white rounded-lg border border-slate-200 p-4 mb-6 shadow-sm">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-700">
                        Vector store search
                      </h3>
                      <p className="text-[11px] text-slate-500">
                        The query was embedded, compared against every vector in the
                        collection, and the top candidates were returned in L2-distance order
                        (lower is closer). Keyword hits are unioned in first, then deduped.
                      </p>
                    </div>
                  </div>

                  {/* Store info strip */}
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4 text-[11px]">
                    <div className="bg-slate-50 border border-slate-200 rounded p-2">
                      <div className="text-[10px] text-slate-500 uppercase">Tenant</div>
                      <div className="font-mono text-slate-800">
                        {stages.rag_retrieval.store.tenant_id}
                      </div>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded p-2">
                      <div className="text-[10px] text-slate-500 uppercase">Collection</div>
                      <div className="font-mono text-slate-800">
                        {stages.rag_retrieval.store.collection_name}
                      </div>
                    </div>
                    <div className="bg-violet-50 border border-violet-200 rounded p-2">
                      <div className="text-[10px] text-violet-600 uppercase">Vectors</div>
                      <div className="font-mono text-violet-900 font-bold">
                        {stages.rag_retrieval.store.count ?? '?'}
                      </div>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded p-2">
                      <div className="text-[10px] text-slate-500 uppercase">Embedder</div>
                      <div className="font-mono text-slate-800 truncate" title={stages.rag_retrieval.store.embedding_model || ''}>
                        {stages.rag_retrieval.store.embedding_model || '—'}
                      </div>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded p-2">
                      <div className="text-[10px] text-slate-500 uppercase">Dim / Device</div>
                      <div className="font-mono text-slate-800">
                        {stages.rag_retrieval.store.embedding_dim || '?'}d ·{' '}
                        {stages.rag_retrieval.store.device || '?'}
                      </div>
                    </div>
                  </div>

                  {/* Query pill */}
                  <div className="mb-3">
                    <div className="text-[10px] text-slate-500 uppercase mb-1">Query embedded</div>
                    <div className="inline-block bg-indigo-50 border border-indigo-200 text-indigo-800 px-2 py-1 rounded text-xs italic">
                      "{trace.query}"
                    </div>
                  </div>

                  {/* Keyword hits */}
                  {stages.rag_retrieval.keyword?.length > 0 && (
                    <div className="mb-4">
                      <div className="text-[10px] text-slate-500 uppercase mb-1">
                        Keyword matches ({stages.rag_retrieval.keyword.length})
                      </div>
                      <div className="space-y-1">
                        {stages.rag_retrieval.keyword.map((e, i) => {
                          const kept = ragCombined.some((k) => k.document === e.document);
                          return (
                            <div
                              key={`kw-${i}`}
                              className="flex items-center gap-3 text-[11px] p-1 rounded hover:bg-slate-50"
                            >
                              <ScoreBar distance={null} kept={kept} />
                              <span className="text-slate-700 truncate flex-1">
                                {(e.document || '').slice(0, 100).replace(/\n/g, ' ')}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Semantic ranking */}
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase mb-1">
                      Semantic top-{stages.rag_retrieval.semantic?.length || 0} (of{' '}
                      {stages.rag_retrieval.store?.count ?? '?'} vectors scanned)
                    </div>
                    {(stages.rag_retrieval.semantic || []).length === 0 ? (
                      <div className="text-xs text-slate-400">no semantic results</div>
                    ) : (
                      <div className="space-y-1">
                        {stages.rag_retrieval.semantic.map((e, i) => {
                          const kept = ragCombined.some(
                            (k) => k.document === e.document && k.source === 'semantic',
                          );
                          const file = e.metadata?.filename || '(unknown)';
                          return (
                            <div
                              key={`sem-${i}`}
                              className="flex items-center gap-3 text-[11px] p-1 rounded hover:bg-slate-50"
                            >
                              <span className="text-slate-400 font-mono w-5 text-right">
                                #{i + 1}
                              </span>
                              <ScoreBar distance={e.score} kept={kept} />
                              <span className="text-slate-700 font-mono truncate flex-1">
                                {file}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Expanded panels */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">
                    Full prompt sent to LLM
                  </h3>
                  <pre className="whitespace-pre-wrap text-[11px] bg-slate-50 border border-slate-200 rounded p-3 max-h-96 overflow-y-auto font-mono">
                    {stages.prompt.full || '(no prompt — fusion was empty)'}
                  </pre>
                </div>
                <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">
                    Retrieved documents (detail)
                  </h3>
                  {ragCombined.length === 0 ? (
                    <div className="text-xs text-slate-500">No documents retrieved.</div>
                  ) : (
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {ragCombined.map((e, i) => (
                        <div key={i} className="border rounded p-2 bg-slate-50">
                          <div className="flex justify-between text-[10px] text-slate-500 mb-1">
                            <span>
                              {e.metadata?.filename || '(unknown)'} · {e.source}
                            </span>
                            <span className="font-mono">
                              dist {e.score != null ? e.score.toFixed(4) : '—'}
                            </span>
                          </div>
                          <pre className="whitespace-pre-wrap text-[11px] font-mono">
                            {e.document}
                          </pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
  );
}
