import React, { useState, useEffect } from 'react';
import { X, Send, MessageSquare, ThumbsUp, ThumbsDown, ShieldAlert } from 'lucide-react';
import { apiFetch } from '../api/client';

export default function ChatWidget({ user, onClose }) {
  const [msg, setMsg] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchMessages = () => {
    apiFetch('/api/chat')
      .then(res => res.json())
      .then(data => {
        if (user.role === 'admin') {
          setMessages(data);
        } else {
          const myMessages = data.filter(m => m.username === user.username || m.username === 'System');
          setMessages(myMessages);
        }
      })
      .catch(err => console.error(err));
  };

  useEffect(() => {
    setLoading(true);
    fetchMessages();
    setLoading(false);
    const interval = setInterval(fetchMessages, 5000);
    return () => clearInterval(interval);
  }, [user]);

  const handleSend = async () => {
    if (!msg) return;

    const newMsg = { id: Date.now(), username: user.name, content: msg, timestamp: 'Just now', type: 'general' };
    setMessages([newMsg, ...messages]);

    await apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ username: user.username, content: msg })
    });
    setMsg('');
    fetchMessages();
  };

  const handleAction = async (targetUsername, action, messageId) => {
    try {
      await apiFetch('/api/chat/handle-request', {
        method: 'POST',
        body: JSON.stringify({ username: targetUsername, action, message_id: messageId })
      });
      fetchMessages();
    } catch (error) {
      alert("Action failed");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-neutral-900/90 backdrop-blur-md w-full max-w-lg h-[600px] flex flex-col rounded-2xl border border-white/[0.08] shadow-2xl">

        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <MessageSquare className="w-5 h-5 text-amber-400" />
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
            </div>
            <h3 className="text-sm font-semibold text-neutral-100">
              {user.role === 'admin' ? 'Admin Command Channel' : 'Support Chat'}
            </h3>
          </div>
          <button onClick={onClose} className="text-neutral-500 hover:text-neutral-200 transition-transform hover:rotate-90"><X className="w-5 h-5" /></button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
          {loading ? <p className="text-neutral-600 text-sm text-center mt-10">Connecting…</p> :
            messages.length === 0 ? <p className="text-neutral-600 text-sm text-center mt-10">No messages yet.</p> :
              messages.map(m => (
                <div key={m.id} className={`relative p-4 rounded-xl border transition-colors ${
                  m.type === 'access_request' ? 'bg-red-500/[0.04] border-red-500/20' :
                  m.type === 'system' ? 'bg-black/20 border-white/[0.05] text-center' :
                  'bg-black/20 border-white/[0.06]'
                }`}>
                  {m.type === 'system' ? (
                    <p className="text-xs text-neutral-500">{m.content}</p>
                  ) : (
                    <>
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          {m.type === 'access_request' && <ShieldAlert className="w-3.5 h-3.5 text-red-400" />}
                          <span className={`text-sm font-semibold ${m.type === 'access_request' ? 'text-red-400' : 'text-amber-400'}`}>
                            {m.username}
                          </span>
                        </div>
                        <span className="text-[10px] text-neutral-600">{m.timestamp}</span>
                      </div>

                      <p className="text-sm text-neutral-300 leading-relaxed mb-3">{m.content}</p>

                      {user.role === 'admin' && m.type === 'access_request' && (
                        <div className="flex gap-2 mt-3 pt-3 border-t border-red-500/10">
                          <button
                            onClick={() => handleAction(m.username, 'approve', m.id)}
                            className="flex-1 flex items-center justify-center gap-2 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500 hover:text-neutral-950 transition-colors text-xs font-semibold uppercase tracking-wider border border-emerald-500/20"
                          >
                            <ThumbsUp className="w-3 h-3" /> Approve
                          </button>
                          <button
                            onClick={() => handleAction(m.username, 'reject', m.id)}
                            className="flex-1 flex items-center justify-center gap-2 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500 hover:text-white transition-colors text-xs font-semibold uppercase tracking-wider border border-red-500/20"
                          >
                            <ThumbsDown className="w-3 h-3" /> Deny
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/[0.06]">
          <div className="flex gap-2">
            <input
              className="flex-1 bg-black/30 border border-white/[0.08] rounded-xl px-4 py-3 text-neutral-100 text-sm focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors placeholder-neutral-600"
              placeholder="Type a message…"
              value={msg}
              onChange={e => setMsg(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
            />
            <button onClick={handleSend} className="p-3 bg-amber-500 hover:bg-amber-400 text-neutral-950 rounded-xl transition-transform active:scale-95">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
