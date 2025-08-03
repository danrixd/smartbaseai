import { useState, useEffect, useCallback, useRef, useContext } from 'react';
import { useLocation } from 'react-router-dom';
import Layout from '../components/Layout';
import api from '../api/api';
import AppContext from '../store/AppContext';

export default function Chat() {
  const location = useLocation();
  const { activeTenant, sessions, setSessions } = useContext(AppContext);
  const [sessionId, setSessionId] = useState(() => {
    const params = new URLSearchParams(location.search);
    return params.get('session') || crypto.randomUUID();
  });
  const [input, setInput] = useState('');
  const [history, setHistory] = useState([]);
  const containerRef = useRef(null);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const sid = params.get('session');
    if (sid) {
      setSessionId(sid);
      setHistory([]);
    }
  }, [location.search]);

  const loadHistory = useCallback(async () => {
    if (!activeTenant) return;
    try {
      const res = await api.get('/chat/history', {
        params: { session_id: sessionId, tenant_id: activeTenant },
      });
      setHistory(res.data.history || []);
    } catch {
      setHistory([]);
    }
  }, [sessionId, activeTenant]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [history]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const tenant = activeTenant || localStorage.getItem('tenant_id');
    if (!tenant) return;

    const msg = input;
    setInput('');
    setHistory((prev) => [...prev, { sender: 'user', message: msg }]);

    try {
      const res = await api.post("/chat/message", {
        session_id: sessionId,
        tenant_id: tenant,
        message: msg,
      });

      const idx = sessions.findIndex((s) => s.id === sessionId);
      let next = [...sessions];
      if (idx === -1) {
        next = [{ id: sessionId, title: msg.slice(0, 30) }, ...sessions];
      } else if (next[idx].title === 'New Chat') {
        next[idx].title = msg.slice(0, 30);
      }
      setSessions(next);
      localStorage.setItem('chat_sessions', JSON.stringify(next));

      setHistory(res.data.history || []);
    } catch (err) {
      console.error(err);
    }
  };

  const examples = [
    'Explain quantum computing in simple terms',
    'Write a poem about artificial intelligence',
    'How do I make an HTTP request in JavaScript?',
  ];

  return (
    <Layout>
      <div className="flex flex-col flex-1 overflow-hidden">
        <div ref={containerRef} className="flex-1 overflow-y-auto p-4 bg-gray-50">
          <div className="max-w-3xl mx-auto space-y-6">
            {history.length === 0 && (
              <div className="text-center py-10">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 flex items-center justify-center">
                  <i className="fas fa-robot text-white text-2xl"></i>
                </div>
                <h2 className="text-2xl font-bold text-gray-800 mb-2">How can I help you today?</h2>
                <p className="text-gray-600">Ask me anything, or try one of these examples:</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-6">
                  {examples.map((ex) => (
                    <button
                      key={ex}
                      className="example-btn bg-white hover:bg-gray-100 border border-gray-200 rounded-lg p-3 text-sm text-left"
                      onClick={() => setInput(ex)}
                    >
                      {`"${ex}"`}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {history.map((msg, idx) => (
              <div key={idx} className="message">
                {msg.sender === 'user' ? (
                  <div className="flex gap-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center">
                      <i className="fas fa-user text-gray-600"></i>
                    </div>
                    <div className="flex-1">
                      <div className="bg-white border border-gray-200 rounded-lg p-4">
                        <p>{msg.message}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center">
                      <i className="fas fa-robot text-white"></i>
                    </div>
                    <div className="flex-1">
                      <div className="bg-gray-100 rounded-lg p-4">
                        <p>{msg.message}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white border-t border-gray-200 p-4">
          <div className="max-w-3xl mx-auto">
            <div className="relative">
              <textarea
                rows="1"
                placeholder="Message AI Assistant..."
                className="w-full p-4 pr-16 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 resize-none transition-all"
                style={{ minHeight: '60px' }}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
              ></textarea>
              <div className="absolute right-3 bottom-3 flex gap-2">
                <button className="text-gray-500 hover:text-gray-700">
                  <i className="fas fa-paperclip"></i>
                </button>
                <button
                  type="button"
                  className="bg-blue-500 hover:bg-blue-600 text-white p-2 rounded-lg transition-colors"
                  onClick={sendMessage}
                >
                  <i className="fas fa-paper-plane"></i>
                </button>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              AI Assistant may produce inaccurate information about people, places, or facts.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}

