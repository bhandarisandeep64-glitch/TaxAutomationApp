import React, { useState, useEffect } from 'react';
import { X, CheckCircle, Send, User, MessageSquare, ThumbsUp, ThumbsDown, ShieldAlert } from 'lucide-react';
import { THEME } from '../constants/theme';

export default function ChatWidget({ user, onClose }) {
  const [msg, setMsg] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchMessages = () => {
    fetch('http://127.0.0.1:5000/api/chat')
        .then(res => res.json())
        .then(data => {
            // Filter logic:
            // Admin sees ALL messages.
            // Regular User sees only THEIR OWN messages or System messages related to them.
            if (user.role === 'admin') {
                setMessages(data);
            } else {
                const myMessages = data.filter(m => m.username === user.username || m.username === 'System');
                setMessages(myMessages);
            }
        })
        .catch(err => console.error(err));
  };

  // Load messages on open
  useEffect(() => {
    setLoading(true);
    fetchMessages();
    setLoading(false);
    // Poll every 5 seconds for real-time feel
    const interval = setInterval(fetchMessages, 5000);
    return () => clearInterval(interval);
  }, [user]);

  const handleSend = async () => {
    if(!msg) return;
    
    // Optimistic UI
    const newMsg = { id: Date.now(), username: user.name, content: msg, timestamp: 'Just now', type: 'general' };
    setMessages([newMsg, ...messages]);
    
    await fetch('http://127.0.0.1:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user.username, content: msg }) // Use username for consistency
    });
    setMsg('');
    fetchMessages(); 
  };

  // Admin Action Handler
  const handleAction = async (targetUsername, action, messageId) => {
      try {
          await fetch('http://127.0.0.1:5000/api/chat/handle-request', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                  username: targetUsername, 
                  action: action,
                  message_id: messageId
              })
          });
          fetchMessages();
      } catch (error) {
          alert("Action failed");
      }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className={`${THEME.card} w-full max-w-lg h-[600px] flex flex-col rounded-xl border ${THEME.borderAccent} shadow-2xl`}>
        
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-2">
             <div className="relative">
                <MessageSquare className={`w-5 h-5 ${THEME.accent}`} />
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
             </div>
             <h3 className={`text-lg font-bold text-white`}>
                 {user.role === 'admin' ? 'Admin Command Channel' : 'Support Chat'}
             </h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-transform hover:rotate-90"><X className="w-5 h-5" /></button>
        </div>
        
        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-slate-950">
             {loading ? <p className="text-slate-500 text-center mt-10">Connecting...</p> : 
             messages.length === 0 ? <p className="text-slate-500 text-center mt-10">No messages yet.</p> : 
             messages.map(m => (
                 <div key={m.id} className={`relative group p-4 rounded-xl border transition-all duration-300 ${
                     m.type === 'access_request' ? 'bg-red-950/20 border-red-900/50 shadow-[0_0_15px_rgba(220,38,38,0.1)]' : 
                     m.type === 'system' ? 'bg-slate-900/50 border-slate-800 text-center' :
                     'bg-slate-900 border-slate-800'
                 }`}>
                     
                     {/* SYSTEM MESSAGE STYLE */}
                     {m.type === 'system' ? (
                         <p className="text-xs text-slate-500 font-mono">{m.content}</p>
                     ) : (
                         // STANDARD MESSAGE STYLE
                         <>
                             <div className="flex justify-between items-start mb-2">
                                 <div className="flex items-center gap-2">
                                    {m.type === 'access_request' && <ShieldAlert className="w-4 h-4 text-red-500 animate-pulse" />}
                                    <span className={`text-sm font-bold ${m.type === 'access_request' ? 'text-red-400' : 'text-amber-500'}`}>
                                        {m.username}
                                    </span>
                                 </div>
                                 <span className="text-[10px] text-slate-600 font-mono">{m.timestamp}</span>
                             </div>
                             
                             <p className="text-sm text-slate-300 leading-relaxed mb-3">{m.content}</p>

                             {/* ACTION BUTTONS (Only for Admin on Requests) */}
                             {user.role === 'admin' && m.type === 'access_request' && (
                                 <div className="flex gap-2 mt-3 pt-3 border-t border-red-900/30">
                                     <button 
                                        onClick={() => handleAction(m.username, 'approve', m.id)}
                                        className="flex-1 flex items-center justify-center gap-2 py-1.5 rounded bg-green-600/20 text-green-400 hover:bg-green-600 hover:text-white transition-all text-xs font-bold uppercase tracking-wider border border-green-900/30"
                                     >
                                        <ThumbsUp className="w-3 h-3" /> Approve
                                     </button>
                                     <button 
                                        onClick={() => handleAction(m.username, 'reject', m.id)}
                                        className="flex-1 flex items-center justify-center gap-2 py-1.5 rounded bg-red-600/20 text-red-400 hover:bg-red-600 hover:text-white transition-all text-xs font-bold uppercase tracking-wider border border-red-900/30"
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
        <div className="p-4 border-t border-slate-800 bg-slate-900">
            <div className="flex gap-2">
                <input 
                   className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-4 py-3 text-white text-sm focus:border-amber-500 outline-none transition-all placeholder-slate-600"
                   placeholder="Type a message..."
                   value={msg}
                   onChange={e => setMsg(e.target.value)}
                   onKeyDown={e => e.key === 'Enter' && handleSend()}
                />
                <button onClick={handleSend} className="p-3 bg-amber-600 hover:bg-amber-500 text-black rounded-lg transition-transform active:scale-95">
                    <Send className="w-4 h-4" />
                </button>
            </div>
        </div>

      </div>
    </div>
  );
}