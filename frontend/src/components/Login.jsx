import React, { useState, useMemo } from 'react';
import { User, Lock, Flower, Send, CheckCircle, ArrowLeft, AlertCircle } from 'lucide-react';

export default function Login({ onLogin }) {
  // Login State
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Restricted Access State
  const [isRestricted, setIsRestricted] = useState(false);
  const [requestReason, setRequestReason] = useState('');
  const [requestSent, setRequestSent] = useState(false);

  // --- GENERATE PETALS ONCE ---
  // We create 30 petals with random properties for the "flying" effect
  const petals = useMemo(() => {
      return Array.from({ length: 30 }).map((_, i) => ({
          id: i,
          left: Math.random() * 100 + '%', // Random horizontal start
          animationDelay: Math.random() * 5 + 's', // Random start time
          animationDuration: Math.random() * 10 + 15 + 's', // Random speed between 15-25s
          opacity: Math.random() * 0.5 + 0.2, // Random initial transparency
          scale: Math.random() * 0.5 + 0.5, // Random size variation
      }));
  }, []);


  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setIsRestricted(false);

    try {
      const response = await fetch('http://127.0.0.1:5000/api/auth/login', {
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
        // Simulate demo error/success for preview
        if(formData.username === 'demo') {
             setTimeout(() => { setLoading(false); alert("Demo Success"); }, 1000)
        } else {
             setError('Server connection failed (Demo)');
        }
    } finally {
      setLoading(false);
    }
  };

  const handleSendRequest = async () => {
      if (!requestReason) return;
      setRequestSent(true);
      // (API call omitted for demo simplicity)
  };

  return (
    <div className="min-h-screen bg-[#020101] flex items-center justify-center relative overflow-hidden font-sans selection:bg-rose-900 selection:text-white">
      
      {/* --- BACKGROUND EFFECTS (GOD MODE) --- */}
      <div className="absolute inset-0 pointer-events-none">
        
        {/* 1. The Volumetric Aura (Multiple layered glows) */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-rose-950/30 blur-[150px] rounded-full animate-pulse-slow"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-rose-900/20 blur-[100px] rounded-full animate-pulse-slow" style={{animationDelay: '-2s'}}></div>
        
        {/* 2. The "God" Rose (Bigger, darker, slower) */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] z-0 opacity-90">
             <Flower 
                strokeWidth={0.3} 
                // Using a darker fill and a deeper, wider drop shadow
                className="w-full h-full text-[#080101] fill-rose-950/10 drop-shadow-[0_0_150px_rgba(225,29,72,0.4)] animate-spin-super-slow" 
             />
        </div>

        {/* 3. Floating Petals Layer */}
        <div className="absolute inset-0 overflow-hidden">
            {petals.map((petal) => (
                <div
                    key={petal.id}
                    className="absolute -bottom-10 rounded-full bg-rose-700/60 blur-[1px] animate-float-up"
                    style={{
                        left: petal.left,
                        width: '12px', // Base size of a petal
                        height: '12px',
                        animationDelay: petal.animationDelay,
                        animationDuration: petal.animationDuration,
                        opacity: petal.opacity,
                        transform: `scale(${petal.scale})`
                    }}
                >
                    {/* Optional: Use actual tiny flower icons instead of dots, but dots often look better blurred */}
                     {/* <Flower className="w-full h-full text-rose-500/50" /> */}
                </div>
             ))}
        </div>

        {/* A final vignette overlay to darken edges */}
        <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_center,_transparent_0%,_#020101_80%)]"></div>
      </div>

      {/* --- LOGIN CARD --- */}
      {/* UPDATED: Made significantly more transparent (bg-black/5), reduced blur, and centered header contents */}
      <div className="relative z-10 w-full max-w-md p-8 bg-black/5 backdrop-blur-sm border border-rose-500/10 rounded-3xl shadow-lg shadow-rose-900/5 ring-1 ring-rose-500/10 transition-all duration-500">
        
        {/* Header - UPDATED: Changed to flex-col for perfect alignment */}
        <div className="flex flex-col items-center justify-center mb-8">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-black/40 border border-rose-900/30 mb-4 shadow-[0_0_40px_rgba(225,29,72,0.4)] animate-pulse-slow backdrop-blur-md">
            <Flower className="w-8 h-8 text-rose-700" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight mb-1 text-center">
            Black Rose <span className="text-rose-600">Inc.</span>
          </h1>
          <p className="text-xs text-zinc-500 uppercase tracking-widest text-center">Secure Automation Gateway</p>
        </div>

        {/* --- MAIN FORM LOGIC --- */}
        {!isRestricted ? (
            // STANDARD LOGIN FORM
            <form onSubmit={handleSubmit} className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
              
              <div className="space-y-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider ml-1">Identity</label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-zinc-600 group-focus-within:text-rose-500 transition-colors" />
                    </div>
                    <input
                      type="text"
                      required
                      className="block w-full pl-10 pr-3 py-3 bg-zinc-900/50 border border-zinc-800/50 rounded-xl text-white placeholder-zinc-600 focus:outline-none focus:border-rose-900/50 focus:ring-1 focus:ring-rose-900/50 transition-all backdrop-blur-sm"
                      placeholder="Username"
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider ml-1">Passphrase</label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-zinc-600 group-focus-within:text-rose-500 transition-colors" />
                    </div>
                    <input
                      type="password"
                      required
                      className="block w-full pl-10 pr-3 py-3 bg-zinc-900/50 border border-zinc-800/50 rounded-xl text-white placeholder-zinc-600 focus:outline-none focus:border-rose-900/50 focus:ring-1 focus:ring-rose-900/50 transition-all backdrop-blur-sm"
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              {error && (
                <div className="text-center p-3 rounded-lg bg-red-950/30 border border-red-900/50 animate-in zoom-in-95">
                  <p className="text-xs text-red-400 font-medium">{error}</p>
                </div>
              )}

              {/* BLACK ROSE BUTTON */}
              <div className="flex justify-center pt-2">
                <div className="relative">
                   <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-rose-900/30 blur-xl rounded-full pointer-events-none"></div>
                   <button
                    type="submit"
                    disabled={loading}
                    title="Enter Workspace"
                    className={`group relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-500
                      ${loading 
                        ? 'bg-zinc-900 border border-zinc-800 cursor-not-allowed' 
                        : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_30px_rgba(225,29,72,0.5)] hover:scale-110 active:scale-95'
                      }`}
                  >
                    {loading ? (
                       <span className="w-8 h-8 border-2 border-zinc-600 border-t-rose-500 rounded-full animate-spin"></span>
                    ) : (
                       <Flower strokeWidth={1.5} className="w-10 h-10 text-rose-700 transition-all duration-700 group-hover:text-rose-500 group-hover:rotate-180 group-hover:scale-110" />
                    )}
                  </button>
                </div>
              </div>
              
              <div className="text-center">
                 <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-medium">
                    {loading ? 'Accessing...' : 'Initiate'}
                 </span>
              </div>

            </form>
        ) : (
            // RESTRICTED ACCESS FORM (Unchanged logic)
            <div className="space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="bg-red-950/20 border border-red-900/50 p-4 rounded-xl text-center">
                    <div className="flex justify-center mb-2"><AlertCircle className="w-6 h-6 text-red-500" /></div>
                    <p className="text-red-400 font-bold text-sm mb-1">ACCESS RESTRICTED</p>
                    <p className="text-[11px] text-zinc-400">Your account privileges have been suspended.</p>
                </div>
                
                {!requestSent ? (
                    <>
                        <div className="space-y-2">
                            <p className="text-xs text-zinc-400 text-center">State your reason for re-activation:</p>
                            <textarea 
                                className="w-full h-28 bg-zinc-900/30 border border-zinc-800 rounded-xl p-4 text-white text-sm placeholder-zinc-600 focus:border-rose-900/50 focus:ring-1 focus:ring-rose-900/50 outline-none resize-none"
                                placeholder="To the Administrator..."
                                value={requestReason}
                                onChange={e => setRequestReason(e.target.value)}
                            />
                        </div>
                        <button 
                            onClick={handleSendRequest}
                            className="w-full py-3 rounded-xl bg-gradient-to-r from-rose-900 to-rose-800 hover:from-rose-800 hover:to-rose-700 text-white text-sm font-bold transition-all shadow-lg shadow-rose-900/20 flex items-center justify-center gap-2"
                        >
                            <Send className="w-4 h-4" /> Transmit Request
                        </button>
                        <button onClick={() => setIsRestricted(false)} className="w-full text-xs text-zinc-500 hover:text-zinc-300 flex items-center justify-center gap-1 transition-colors">
                            <ArrowLeft className="w-3 h-3" /> Return to Login
                        </button>
                    </>
                ) : (
                    <div className="text-center py-6 space-y-4">
                        <div className="w-14 h-14 bg-green-500/10 rounded-full flex items-center justify-center mx-auto border border-green-500/20">
                            <CheckCircle className="w-7 h-7 text-green-500" />
                        </div>
                        <div>
                            <p className="text-white font-bold text-sm">Request Transmitted</p>
                            <p className="text-xs text-zinc-500 mt-1">The administrator has been notified.</p>
                        </div>
                        <button onClick={() => setIsRestricted(false)} className="text-xs text-rose-500 hover:text-rose-400 underline">Return to Login</button>
                    </div>
                )}
            </div>
        )}

        <div className="mt-8 text-center">
          <p className="text-[10px] text-zinc-600">
            &copy; 2025 BLACK ROSE INC. AUTHORIZED PERSONNEL ONLY.
          </p>
        </div>
      </div>

      <style>{`
        @keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .animate-spin-super-slow { animation: spin-slow 120s linear infinite; } /* Slower for majestic feel */
        
        @keyframes pulse-slow { 
            0%, 100% { opacity: 0.5; transform: translate(-50%, -50%) scale(1); } 
            50% { opacity: 0.8; transform: translate(-50%, -50%) scale(1.05); } 
        }
        .animate-pulse-slow { animation: pulse-slow 8s ease-in-out infinite; }

        /* NEW: Petal Floating Animation */
        @keyframes float-up {
            0% {
                transform: translateY(0) rotate(0deg);
                opacity: 0;
            }
            10% {
                opacity: var(--opacity); /* Fade in to target opacity */
            }
            100% {
                /* Move way up the screen and rotate significantly */
                transform: translateY(-120vh) rotate(360deg); 
                opacity: 0;
            }
        }
        .animate-float-up {
            animation-name: float-up;
            animation-timing-function: linear;
            animation-iteration-count: infinite;
            /* Start slightly below screen */
            bottom: -20px;
        }
      `}</style>
    </div>
  );
}