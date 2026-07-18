import React, { useState } from 'react';
import { User, Lock, Send, CheckCircle, ArrowLeft, AlertCircle, ShieldCheck } from 'lucide-react';
import { apiFetch, setToken } from '../api/client';
import PeepalLeaf from './icons/PeepalLeaf';

export default function Login({ onLogin }) {
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isRestricted, setIsRestricted] = useState(false);
  const [requestReason, setRequestReason] = useState('');
  const [requestSent, setRequestSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setIsRestricted(false);

    try {
      const response = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (response.ok) {
        setToken(data.token);
        onLogin(data.user);
      } else {
        setError(data.error || 'Invalid credentials');
        if (data.error && data.error.includes("Restricted")) {
          setIsRestricted(true);
        }
      }
    } catch (err) {
      setError('Server connection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSendRequest = () => {
    if (!requestReason) return;
    setRequestSent(true);
  };

  return (
    <div className="relative min-h-screen w-full bg-neutral-950 flex items-center justify-center overflow-hidden font-sans selection:bg-amber-500/20 selection:text-amber-100">

      {/* Ambient backdrop -- restrained, not theatrical */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(255,255,255,0.03),_transparent_60%)]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[500px] bg-green-950/20 blur-[160px] rounded-full" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:56px_56px]" />
      </div>

      <div className="relative z-10 w-full max-w-[420px] mx-4">
        <div className="rounded-2xl border border-white/[0.07] bg-neutral-900/70 backdrop-blur-2xl shadow-2xl shadow-black/60 p-8 md:p-10">

          {/* Brand */}
          <div className="flex flex-col items-center mb-9 space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-neutral-950 border border-green-900/40 flex items-center justify-center shadow-[0_0_24px_rgba(20,83,45,0.2)]">
              <PeepalLeaf className="w-6 h-6 text-green-800" strokeWidth={1.5} />
            </div>
            <div className="text-center">
              <h1 className="text-xl font-semibold text-neutral-50 tracking-[0.08em]">BG CORP GLOBAL</h1>
              <div className="flex items-center justify-center gap-1.5 mt-1.5">
                <ShieldCheck className="w-3 h-3 text-amber-500/70" />
                <p className="text-[10px] font-medium text-neutral-500 uppercase tracking-[0.2em]">Client Workspace</p>
              </div>
            </div>
          </div>

          {!isRestricted ? (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-neutral-500 pl-0.5">Username</label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-600" />
                  <input
                    type="text"
                    className="block w-full pl-10 pr-4 py-3 bg-black/30 border border-white/[0.08] rounded-xl text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors"
                    placeholder="Enter your username"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-neutral-500 pl-0.5">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-600" />
                  <input
                    type="password"
                    className="block w-full pl-10 pr-4 py-3 bg-black/30 border border-white/[0.08] rounded-xl text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors"
                    placeholder="••••••••••••"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  />
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2.5 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-neutral-950 text-sm font-semibold transition-colors disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-amber-500/10"
              >
                {loading ? 'Signing in…' : 'Sign In'}
              </button>
            </form>
          ) : (
            <div className="space-y-6">
              <div className="bg-red-500/5 border border-red-500/20 p-5 rounded-xl flex flex-col items-center text-center gap-3">
                <div className="w-11 h-11 rounded-full bg-red-500/10 flex items-center justify-center">
                  <Lock className="w-5 h-5 text-red-500" />
                </div>
                <div>
                  <h3 className="text-red-400 font-semibold text-sm">Access Suspended</h3>
                  <p className="text-xs text-neutral-500 mt-1">This account is restricted. Contact your administrator to request access.</p>
                </div>
              </div>

              {!requestSent ? (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-neutral-500 pl-0.5">Reason for access</label>
                    <textarea
                      value={requestReason}
                      onChange={(e) => setRequestReason(e.target.value)}
                      className="w-full h-24 bg-black/30 border border-white/[0.08] rounded-xl p-3 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 resize-none transition-colors"
                      placeholder="Briefly explain why you need access…"
                    />
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => setIsRestricted(false)}
                      className="flex-1 py-2.5 rounded-xl border border-white/[0.08] text-neutral-400 hover:text-neutral-100 hover:bg-white/[0.04] transition-colors text-xs font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSendRequest}
                      className="flex-[2] py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-neutral-950 text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
                    >
                      <Send className="w-3.5 h-3.5" /> Send Request
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-6 flex flex-col items-center">
                  <div className="w-14 h-14 bg-emerald-500/10 rounded-full flex items-center justify-center mb-4 border border-emerald-500/20">
                    <CheckCircle className="w-6 h-6 text-emerald-400" />
                  </div>
                  <h3 className="text-neutral-100 font-medium text-sm">Request Sent</h3>
                  <p className="text-neutral-500 text-xs mt-1 mb-6 text-center max-w-[220px]">Your admin has been notified and will review your request shortly.</p>
                  <button onClick={() => setIsRestricted(false)} className="flex items-center gap-2 text-xs text-neutral-500 hover:text-neutral-200 transition-colors">
                    <ArrowLeft className="w-3 h-3" /> Return to sign in
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        <p className="text-center text-[10px] text-neutral-700 mt-6 uppercase tracking-[0.2em]">Secure Connection · TLS 1.3</p>
      </div>
    </div>
  );
}
