import { useContext, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import api from '../api/api';
import AppContext from '../store/AppContext';
import VaultGate from '../components/VaultGate';
import FileTree from '../components/FileTree';

export default function Vault() {
  const { activeTenant, tenants } = useContext(AppContext);
  const role = localStorage.getItem('role');

  const [tenantId, setTenantId] = useState(
    activeTenant || localStorage.getItem('tenant_id') || '',
  );
  const [files, setFiles] = useState([]);
  const [selected, setSelected] = useState(null);
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [flash, setFlash] = useState('');
  const [viewMode, setViewMode] = useState('edit'); // 'edit' | 'preview' | 'split'

  useEffect(() => {
    if (activeTenant) setTenantId(activeTenant);
  }, [activeTenant]);

  const loadFiles = async (tid) => {
    setLoading(true);
    try {
      const res = await api.get('/files/vault', { params: { tenant_id: tid } });
      setFiles(res.data.files || []);
    } catch (err) {
      setFiles([]);
      setFlash(err.response?.data?.detail || 'Failed to list vault files');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setSelected(null);
    setContent('');
    setOriginalContent('');
    if (tenantId) loadFiles(tenantId);
    else setFiles([]);
  }, [tenantId]);

  const open = async (filename) => {
    setLoading(true);
    try {
      const res = await api.get(`/files/vault/${filename}`, {
        params: { tenant_id: tenantId },
      });
      setSelected(filename);
      setContent(res.data.content);
      setOriginalContent(res.data.content);
      setFlash('');
    } catch (err) {
      setFlash(err.response?.data?.detail || 'Failed to load file');
    } finally {
      setLoading(false);
    }
  };

  const save = async () => {
    if (!selected) return;
    setLoading(true);
    try {
      await api.put(
        `/files/vault/${selected}`,
        { content },
        { params: { tenant_id: tenantId } },
      );
      setOriginalContent(content);
      setFlash(`Saved ${selected} and re-ingested into the ${tenantId} vault.`);
      setTimeout(() => setFlash(''), 4000);
    } catch (err) {
      setFlash(err.response?.data?.detail || 'Save failed');
    } finally {
      setLoading(false);
    }
  };

  const upload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    setLoading(true);
    let ingested = 0;
    let failed = 0;
    let lastName = '';
    try {
      for (const file of files) {
        try {
          const fd = new FormData();
          fd.append('file', file);
          const res = await api.post('/files/upload', fd, {
            params: { tenant_id: tenantId },
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          if (res.data?.ingested) ingested += 1;
          lastName = file.name;
        } catch {
          failed += 1;
        }
      }
      await loadFiles(tenantId);
      setFlash(
        files.length === 1
          ? (ingested
              ? `Uploaded ${lastName} and ingested into the ${tenantId} vault.`
              : `Uploaded ${lastName} (type not ingestible — saved but not embedded).`)
          : `Uploaded ${files.length - failed}/${files.length} files · ${ingested} ingested.`,
      );
      setTimeout(() => setFlash(''), 5000);
      if (files.length === 1 && lastName) open(lastName);
    } finally {
      setLoading(false);
      e.target.value = '';
    }
  };

  const dirty = selected && content !== originalContent;

  const vaultList = (role === 'super_admin' ? tenants : [tenantId]).filter(Boolean);

  if (!tenantId) {
    return <VaultGate role={role} title="Pick a vault to browse and edit its files" />;
  }

  return (
    <div className="flex-1 overflow-hidden bg-slate-50 p-6 flex flex-col">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Vault Editor</h1>
            <p className="text-sm text-slate-600 mt-1">
              Edit ingested knowledge-vault files. Saving overwrites the source document and
              automatically re-embeds it into the tenant's Chroma collection so the next chat
              query retrieves the updated text — no rebuild needed.
            </p>
          </div>
          {role === 'super_admin' && (
            <div>
              <label className="block text-[11px] text-slate-500 mb-1">Vault</label>
              <select
                className="px-2 py-1 border border-slate-300 rounded text-sm"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
              >
                {vaultList.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {flash && (
          <div className="mb-3 text-sm bg-indigo-50 text-indigo-800 border border-indigo-200 rounded p-2">
            {flash}
          </div>
        )}

        <div className="flex-1 grid grid-cols-1 md:grid-cols-[260px_1fr] gap-4 min-h-0">
          {/* File list */}
          <div className="bg-white border border-slate-200 rounded p-3 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-2 flex-shrink-0">
              <div className="text-xs font-semibold text-slate-500 uppercase">
                {tenantId}
              </div>
              <label className="text-[11px] text-indigo-600 hover:text-indigo-800 cursor-pointer">
                + Add files
                <input
                  type="file"
                  className="hidden"
                  accept=".md,.markdown,.txt,.csv,.log"
                  onChange={upload}
                  multiple
                />
              </label>
            </div>
            <FileTree files={files} selected={selected} onOpen={open} loading={loading} />
            <div className="text-[10px] text-slate-400 mt-2 pt-2 border-t border-slate-100 flex-shrink-0">
              Supports .md, .txt, .csv, .log — uploaded files are auto-embedded.
            </div>
          </div>

          {/* Editor */}
          <div className="bg-white border border-slate-200 rounded p-3 flex flex-col min-h-0">
            {!selected ? (
              <div className="m-auto text-slate-400 text-sm">
                Select a file on the left to edit it.
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
                  <div className="text-sm font-semibold text-slate-700 font-mono truncate flex-1 min-w-0">
                    {selected}
                  </div>
                  <div className="flex items-center gap-1 bg-slate-100 border border-slate-200 rounded p-0.5">
                    {['edit', 'split', 'preview'].map((m) => (
                      <button
                        key={m}
                        className={`text-[11px] px-2 py-0.5 rounded ${
                          viewMode === m
                            ? 'bg-white text-slate-800 shadow-sm'
                            : 'text-slate-500 hover:text-slate-700'
                        }`}
                        onClick={() => setViewMode(m)}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      className="px-3 py-1 text-xs bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded disabled:opacity-50"
                      onClick={() => setContent(originalContent)}
                      disabled={!dirty}
                    >
                      Revert
                    </button>
                    <button
                      className="px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-700 text-white rounded disabled:bg-slate-400"
                      onClick={save}
                      disabled={!dirty || loading}
                    >
                      {loading ? 'Saving…' : 'Save + re-ingest'}
                    </button>
                  </div>
                </div>
                <div className={`flex-1 min-h-0 ${viewMode === 'split' ? 'grid grid-cols-2 gap-2' : ''}`}>
                  {viewMode !== 'preview' && (
                    <textarea
                      className="w-full h-full p-3 text-xs font-mono border border-slate-300 rounded resize-none focus:outline-none focus:border-indigo-400"
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      spellCheck={false}
                    />
                  )}
                  {viewMode !== 'edit' && (
                    <div className="w-full h-full p-3 border border-slate-200 rounded overflow-y-auto bg-slate-50 prose prose-sm max-w-none">
                      <ReactMarkdown>{content}</ReactMarkdown>
                    </div>
                  )}
                </div>
                {dirty && (
                  <div className="text-[11px] text-amber-600 mt-1 flex-shrink-0">
                    Unsaved changes — the vault will re-embed this file on save.
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
  );
}
