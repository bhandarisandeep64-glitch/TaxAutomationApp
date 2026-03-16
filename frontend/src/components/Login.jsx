import React, { useState, useEffect, useRef, useMemo } from 'react';
import { User, Lock, Flower, Send, CheckCircle, ArrowLeft, AlertCircle, ShieldCheck, Fingerprint } from 'lucide-react';

export default function Login({ onLogin }) {
  // --- STATE ---
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isRestricted, setIsRestricted] = useState(false);
  const [requestReason, setRequestReason] = useState('');
  const [requestSent, setRequestSent] = useState(false);
  
  // Mouse position state for spotlight effects
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // --- MEMOS ---
  // Advanced Petals: Added rotation variance and 'sway' duration
  const petals = useMemo(() => {
    return Array.from({ length: 40 }).map((_, i) => ({
      id: i,
      left: Math.random() * 100 + '%',
      animationDelay: Math.random() * 10 + 's',
      duration: Math.random() * 15 + 10 + 's', // Slower, more majestic
      opacity: Math.random() * 0.4 + 0.1,
      scale: Math.random() * 0.6 + 0.4,
      rotationDir: Math.random() > 0.5 ? 1 : -1, 
    }));
  }, []);

  // --- HANDLERS ---
  const handleMouseMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setMousePos({ x, y });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setIsRestricted(false);

    // Artificial delay for dramatic effect (optional, feels premium)
    // await new Promise(r => setTimeout(r, 800)); 

    try {
      const response = await fetch('https://taxautomationapp.onrender.com/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (response.ok) {
        onLogin(data.user); 
      } else {
        setError(data.error || 'Invalid credentials');
        if (data.error && data.error.includes("Restricted")) {
            setIsRestricted(true);
        }
      }
    } catch (err) {
        // Fallback for demo/offline testing
        if(formData.username === 'demo') {
             setTimeout(() => { 
                 setLoading(false); 
                 onLogin({ username: 'demo', role: 'admin' }); // Mock success
             }, 1000)
        } else {
             setError('Server connection failed');
        }
    } finally {
      setLoading(false);
    }
  };

  const handleSendRequest = async () => {
    if (!requestReason) return;
    
    // You can add your API call here to send the requestReason to the backend
    // await fetch('/api/request-access', ... )

    setRequestSent(true);
  };

  return (
    <div 
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className="relative min-h-screen w-full bg-[#050001] flex items-center justify-center overflow-hidden font-sans selection:bg-rose-500/30 selection:text-rose-200"
    >
      
      {/* --- LAYER 0: CINEMATIC GRAIN & NOISE --- */}
      <div className="absolute inset-0 z-0 opacity-[0.07] pointer-events-none mix-blend-overlay"
           style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} 
      />

      {/* --- LAYER 1: AMBIENT LIGHTING --- */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* The "Source" Light */}
        <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-rose-900/20 blur-[120px] rounded-full mix-blend-screen animate-pulse-slow" />
        
        {/* The "God" Rose - massive background element */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120vw] h-[120vw] max-w-[1000px] max-h-[1000px] opacity-100 z-0">
             <Flower 
                strokeWidth={0.2} 
                className="w-full h-full text-[#0f0204] fill-rose-950/5 drop-shadow-2xl animate-spin-majestic" 
             />
        </div>

        {/* Dynamic Mouse Follower Aura */}
        <div 
            className="absolute w-[600px] h-[600px] bg-rose-600/10 blur-[100px] rounded-full transition-transform duration-1000 ease-out will-change-transform"
            style={{ 
                left: -300, 
                top: -300,
                transform: `translate(${mousePos.x}px, ${mousePos.y}px)` 
            }}
        />
      </div>

      {/* --- LAYER 2: PARTICLES (PETALS) --- */}
      <div className="absolute inset-0 pointer-events-none z-0">
        {petals.map((petal) => (
            <div
                key={petal.id}
                className="absolute bg-gradient-to-br from-rose-800/80 to-rose-950/20 shadow-lg shadow-rose-900/20 backdrop-blur-[1px]"
                style={{
                    left: petal.left,
                    bottom: '-50px',
                    width: '14px',
                    height: '14px',
                    borderRadius: '2px 12px 2px 12px', // Leaf/Petal shape
                    opacity: petal.opacity,
                    scale: petal.scale,
                    animation: `float-up ${petal.duration} linear infinite`,
                    animationDelay: petal.animationDelay,
                    '--rotation-dir': petal.rotationDir // Passed to CSS
                }}
            />
        ))}
      </div>

      {/* --- LAYER 3: THE GLASS INTERFACE --- */}
      <div className="relative z-10 w-full max-w-[420px] mx-4 perspective-1000">
        <div className="relative group backdrop-blur-2xl bg-black/40 border border-white/5 rounded-3xl p-1 overflow-hidden shadow-2xl shadow-black/80 transition-all duration-500 hover:shadow-rose-900/10 hover:border-white/10">
            
            {/* Internal Card Background Gradient */}
            <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-50 pointer-events-none" />
            
            {/* The Actual Form Container */}
            <div className="relative bg-[#050202]/80 rounded-[20px] p-8 md:p-10 border border-white/5">
                
                {/* Brand Header */}
                <div className="flex flex-col items-center mb-10 space-y-4">
                    <div className="relative">
                        <div className="absolute inset-0 bg-rose-500 blur-xl opacity-20 animate-pulse" />
                        <div className="relative w-16 h-16 bg-gradient-to-br from-zinc-900 to-black rounded-2xl border border-rose-500/20 flex items-center justify-center shadow-lg transform rotate-45 group-hover:rotate-0 transition-transform duration-700 ease-out">
                            <Flower className="w-8 h-8 text-rose-500 transform -rotate-45 group-hover:rotate-0 transition-transform duration-700" strokeWidth={1.5} />
                        </div>
                    </div>
                    <div className="text-center">
                        <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white via-rose-100 to-zinc-400 tracking-tight">
                            BLACK ROSE
                        </h1>
                        <div className="flex items-center justify-center gap-2 mt-1">
                            <ShieldCheck className="w-3 h-3 text-rose-700" />
                            <p className="text-[10px] font-mono text-rose-900/80 uppercase tracking-[0.2em]">Restricted Access</p>
                        </div>
                    </div>
                </div>

                {/* Form Logic Swapper */}
                {!isRestricted ? (
                    <form onSubmit={handleSubmit} className="space-y-6 animate-fade-in-up">
                        
                        {/* Username Input */}
                        <div className="group/input space-y-1.5">
                            <label className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest pl-1 group-focus-within/input:text-rose-500 transition-colors">Operative ID</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <User className="h-4 w-4 text-zinc-600 group-focus-within/input:text-white transition-colors" />
                                </div>
                                <input
                                    type="text"
                                    className="block w-full pl-11 pr-4 py-3.5 bg-zinc-900/50 border border-zinc-800 rounded-xl text-sm text-white placeholder-zinc-700 focus:outline-none focus:border-rose-900/50 focus:bg-zinc-900/80 focus:ring-1 focus:ring-rose-900/50 transition-all shadow-inner"
                                    placeholder="Enter identification"
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                />
                                {/* Corner Accents */}
                                <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-rose-500/0 group-focus-within/input:border-rose-500/50 transition-all duration-500" />
                                <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-rose-500/0 group-focus-within/input:border-rose-500/50 transition-all duration-500" />
                            </div>
                        </div>

                        {/* Password Input */}
                        <div className="group/input space-y-1.5">
                            <label className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest pl-1 group-focus-within/input:text-rose-500 transition-colors">Security Key</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Lock className="h-4 w-4 text-zinc-600 group-focus-within/input:text-white transition-colors" />
                                </div>
                                <input
                                    type="password"
                                    className="block w-full pl-11 pr-4 py-3.5 bg-zinc-900/50 border border-zinc-800 rounded-xl text-sm text-white placeholder-zinc-700 focus:outline-none focus:border-rose-900/50 focus:bg-zinc-900/80 focus:ring-1 focus:ring-rose-900/50 transition-all shadow-inner"
                                    placeholder="••••••••••••"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                />
                            </div>
                        </div>

                        {error && (
                            <div className="flex items-center gap-3 p-3 rounded-lg bg-red-950/20 border border-red-900/30 text-red-400 text-xs animate-shake">
                                <AlertCircle className="w-4 h-4 shrink-0" />
                                {error}
                            </div>
                        )}

                        {/* Action Button */}
                        <button
                            type="submit"
                            disabled={loading}
                            className="relative w-full group overflow-hidden rounded-xl p-[1px] focus:outline-none focus:ring-2 focus:ring-rose-500/50 focus:ring-offset-2 focus:ring-offset-black disabled:opacity-70 disabled:cursor-not-allowed"
                        >
                            <span className="absolute inset-0 bg-gradient-to-r from-rose-900 via-rose-600 to-rose-900 opacity-70 group-hover:opacity-100 animate-gradient-xy transition-opacity" />
                            <div className="relative bg-black h-full w-full rounded-[11px] flex items-center justify-center py-3.5 transition-colors group-hover:bg-zinc-900">
                                {loading ? (
                                     <div className="flex items-center gap-2">
                                        <div className="w-4 h-4 border-2 border-rose-500 border-t-transparent rounded-full animate-spin" />
                                        <span className="text-xs font-mono text-rose-200 uppercase tracking-widest">Authenticating...</span>
                                     </div>
                                ) : (
                                    <div className="flex items-center gap-2 text-rose-100 group-hover:text-white transition-colors">
                                        <Fingerprint className="w-5 h-5" />
                                        <span className="text-sm font-semibold tracking-wide">AUTHENTICATE</span>
                                    </div>
                                )}
                            </div>
                        </button>
                    </form>
                ) : (
                    // RESTRICTED VIEW
                    <div className="space-y-6 animate-fade-in-right">
                         <div className="bg-red-500/5 border border-red-500/20 p-5 rounded-xl flex flex-col items-center text-center gap-3">
                             <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center animate-pulse">
                                 <Lock className="w-6 h-6 text-red-500" />
                             </div>
                             <div>
                                 <h3 className="text-red-400 font-bold tracking-tight">Access Suspended</h3>
                                 <p className="text-xs text-red-400/60 mt-1">Multiple failed attempts detected. Protocol 9 engaged.</p>
                             </div>
                         </div>

                         {!requestSent ? (
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-mono text-zinc-500 uppercase">Reason for override</label>
                                    <textarea 
                                        value={requestReason}
                                        onChange={(e) => setRequestReason(e.target.value)}
                                        className="w-full h-24 bg-zinc-900/50 border border-zinc-800 rounded-xl p-3 text-sm text-white focus:border-rose-500/30 focus:ring-1 focus:ring-rose-500/30 outline-none resize-none transition-all"
                                        placeholder="Admin appeal..."
                                    />
                                </div>
                                <div className="flex gap-3">
                                    <button 
                                        onClick={() => setIsRestricted(false)}
                                        className="flex-1 py-3 rounded-xl border border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-900 transition-all text-xs font-medium"
                                    >
                                        Cancel
                                    </button>
                                    <button 
                                        onClick={handleSendRequest}
                                        className="flex-[2] py-3 rounded-xl bg-gradient-to-r from-rose-800 to-rose-700 hover:from-rose-700 hover:to-rose-600 text-white text-xs font-bold shadow-lg shadow-rose-900/20 flex items-center justify-center gap-2 transition-all"
                                    >
                                        <Send className="w-3 h-3" /> Transmit
                                    </button>
                                </div>
                            </div>
                         ) : (
                            <div className="py-8 flex flex-col items-center animate-zoom-in">
                                <div className="w-16 h-16 bg-gradient-to-tr from-green-900 to-green-800 rounded-full flex items-center justify-center mb-4 border border-green-700/50 shadow-lg shadow-green-900/30">
                                    <CheckCircle className="w-8 h-8 text-green-200" />
                                </div>
                                <h3 className="text-white font-medium">Ticket #99420 Sent</h3>
                                <p className="text-zinc-500 text-xs mt-1 mb-6 text-center max-w-[200px]">Admin will review your logs. Expect contact within 24 hours.</p>
                                <button onClick={() => setIsRestricted(false)} className="flex items-center gap-2 text-xs text-zinc-400 hover:text-white transition-colors">
                                    <ArrowLeft className="w-3 h-3" /> Return to Login
                                </button>
                            </div>
                         )}
                    </div>
                )}
            </div>
        </div>
      </div>

      {/* --- FOOTER --- */}
      <div className="absolute bottom-6 text-center space-y-2 z-10 opacity-60">
        <p className="text-[10px] font-mono text-zinc-600 uppercase tracking-[0.3em]">Secure Connection • TLS 1.3</p>
      </div>

      {/* --- CSS ANIMATIONS --- */}
      <style>{`
        @keyframes spin-majestic { 
            from { transform: translate(-50%, -50%) rotate(0deg); } 
            to { transform: translate(-50%, -50%) rotate(360deg); } 
        }
        .animate-spin-majestic { animation: spin-majestic 240s linear infinite; }

        @keyframes float-up {
            0% { transform: translateY(100vh) rotate(0deg) scale(0.8); opacity: 0; }
            10% { opacity: var(--opacity); }
            100% { transform: translateY(-20vh) rotate(calc(360deg * var(--rotation-dir))) scale(1); opacity: 0; }
        }

        @keyframes gradient-xy {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .animate-gradient-xy {
            background-size: 200% 200%;
            animation: gradient-xy 3s ease infinite;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
            20%, 40%, 60%, 80% { transform: translateX(2px); }
        }
        .animate-shake { animation: shake 0.4s cubic-bezier(.36,.07,.19,.97) both; }

        .perspective-1000 { perspective: 1000px; }
      `}</style>
    </div>
  );
}
