import { useMemo, useState, useEffect } from 'react';

/**
 * Interactive file browser for a vault.
 *
 * Features:
 *  - Groups files by first path segment (per-ticker folders for financebench,
 *    a single "(root)" group for flat tenants like personal/company).
 *  - Live search box that filters files and folders by substring. Matching
 *    substrings are highlighted inline. When a query is active, all matching
 *    folders auto-expand; clearing the query restores the user's manual
 *    expand/collapse state.
 *  - Collapsed folders by default so big vaults (financebench has 1,744 files
 *    across 506 folders) don't flood the sidebar.
 *  - File icon + size suffix for visual scanning.
 *  - "Expand all" / "Collapse all" shortcuts.
 */

const FILE_ICONS = {
  '.md': '📄',
  '.markdown': '📄',
  '.txt': '📄',
  '.csv': '📊',
  '.log': '📜',
};

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function highlight(text, query) {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-yellow-200 text-slate-900 rounded-sm px-0.5">
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}

export default function FileTree({ files, selected, onOpen, loading }) {
  const [query, setQuery] = useState('');
  const [userOpen, setUserOpen] = useState({}); // manual open state per folder
  const [allMode, setAllMode] = useState(null); // 'all' | 'none' | null

  // Group files into folders
  const groups = useMemo(() => {
    const g = new Map();
    const root = [];
    for (const f of files) {
      const parts = f.filename.split('/');
      if (parts.length === 1) {
        root.push(f);
      } else {
        const folder = parts[0];
        if (!g.has(folder)) g.set(folder, []);
        g.get(folder).push({ ...f, basename: parts.slice(1).join('/') });
      }
    }
    return { root, folders: Array.from(g.entries()).sort() };
  }, [files]);

  // Compute filtered view
  const q = query.trim().toLowerCase();
  const filtered = useMemo(() => {
    if (!q) return groups;
    const out = { root: [], folders: [] };
    for (const f of groups.root) {
      if (f.filename.toLowerCase().includes(q)) out.root.push(f);
    }
    for (const [folder, entries] of groups.folders) {
      const folderMatches = folder.toLowerCase().includes(q);
      const matched = entries.filter((e) => {
        if (folderMatches) return true;
        return (
          e.basename.toLowerCase().includes(q) ||
          e.filename.toLowerCase().includes(q)
        );
      });
      if (matched.length > 0) out.folders.push([folder, matched]);
    }
    return out;
  }, [groups, q]);

  // When there's a query, all result-folders auto-expand. Without a query,
  // defer to userOpen / allMode. Any folder containing the selected file also
  // auto-expands so the highlighted row is visible.
  const isOpen = (folder) => {
    if (q) return true;
    if (allMode === 'all') return true;
    if (allMode === 'none') return false;
    if (userOpen[folder]) return true;
    if (selected && selected.startsWith(folder + '/')) return true;
    return false;
  };

  const toggle = (folder) => {
    setAllMode(null);
    setUserOpen((prev) => ({ ...prev, [folder]: !prev[folder] }));
  };

  const totalFiles = groups.root.length + groups.folders.reduce((n, [, e]) => n + e.length, 0);
  const shownFiles = filtered.root.length + filtered.folders.reduce((n, [, e]) => n + e.length, 0);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Search + actions */}
      <div className="flex flex-col gap-2 mb-2 flex-shrink-0">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={`Search ${totalFiles} files…`}
          className="w-full text-xs px-2 py-1.5 border border-slate-300 rounded focus:outline-none focus:border-indigo-400"
        />
        <div className="flex items-center justify-between text-[10px] text-slate-500">
          <span>
            {q ? (
              <>
                <b className="text-slate-700">{shownFiles}</b> of {totalFiles} match
              </>
            ) : (
              <>
                {totalFiles} files · {groups.folders.length} folders
              </>
            )}
          </span>
          {!q && (
            <div className="flex gap-1">
              <button
                className="text-[10px] px-1.5 py-0.5 rounded hover:bg-slate-100 border border-slate-200"
                onClick={() => {
                  setAllMode('all');
                  setUserOpen({});
                }}
                title="Expand all folders"
              >
                expand all
              </button>
              <button
                className="text-[10px] px-1.5 py-0.5 rounded hover:bg-slate-100 border border-slate-200"
                onClick={() => {
                  setAllMode('none');
                  setUserOpen({});
                }}
                title="Collapse all folders"
              >
                collapse
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Tree body */}
      <div className="flex-1 overflow-y-auto pr-1">
        {loading && <div className="text-xs text-slate-400">loading…</div>}

        {!loading && totalFiles === 0 && (
          <div className="text-xs text-slate-400">no files yet — click + Add file</div>
        )}

        {!loading && shownFiles === 0 && q && (
          <div className="text-xs text-slate-400">no match for "{query}"</div>
        )}

        {/* Root (flat) files */}
        {filtered.root.length > 0 && (
          <ul className="space-y-0.5 mb-2">
            {filtered.root.map((f) => {
              const icon = FILE_ICONS[f.suffix] || '📄';
              const isSel = selected === f.filename;
              return (
                <li key={f.filename}>
                  <button
                    className={`w-full text-left text-xs px-2 py-1 rounded flex items-center gap-1.5 ${
                      isSel
                        ? 'bg-indigo-100 text-indigo-800'
                        : 'hover:bg-slate-100 text-slate-700'
                    }`}
                    onClick={() => onOpen(f.filename)}
                    title={`${f.size} bytes`}
                  >
                    <span className="flex-shrink-0">{icon}</span>
                    <span className="flex-1 truncate font-mono">
                      {highlight(f.filename, q)}
                    </span>
                    <span className="text-[10px] text-slate-400 flex-shrink-0">
                      {formatBytes(f.size)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {/* Folder groups */}
        <ul className="space-y-0.5">
          {filtered.folders.map(([folder, entries]) => {
            const open = isOpen(folder);
            return (
              <li key={folder}>
                <button
                  className="w-full text-left text-xs px-1 py-0.5 rounded flex items-center gap-1 hover:bg-slate-100 font-semibold text-slate-700"
                  onClick={() => toggle(folder)}
                >
                  <span className="flex-shrink-0 text-slate-500 w-3 text-center">
                    {open ? '▾' : '▸'}
                  </span>
                  <span className="flex-shrink-0">📁</span>
                  <span className="flex-1 truncate">{highlight(folder, q)}</span>
                  <span className="text-[10px] text-slate-400 font-normal flex-shrink-0">
                    {entries.length}
                  </span>
                </button>
                {open && (
                  <ul className="ml-4 border-l border-slate-200 pl-2 space-y-0.5 mt-0.5 mb-1">
                    {entries.map((f) => {
                      const icon = FILE_ICONS[f.suffix] || '📄';
                      const isSel = selected === f.filename;
                      return (
                        <li key={f.filename}>
                          <button
                            className={`w-full text-left text-[11px] px-1.5 py-0.5 rounded flex items-center gap-1.5 ${
                              isSel
                                ? 'bg-indigo-100 text-indigo-800'
                                : 'hover:bg-slate-100 text-slate-600'
                            }`}
                            onClick={() => onOpen(f.filename)}
                            title={`${f.filename} · ${f.size} bytes`}
                          >
                            <span className="flex-shrink-0">{icon}</span>
                            <span className="flex-1 truncate font-mono">
                              {highlight(f.basename, q)}
                            </span>
                            <span className="text-[10px] text-slate-400 flex-shrink-0">
                              {formatBytes(f.size)}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
