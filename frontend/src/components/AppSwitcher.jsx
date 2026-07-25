import React, { useState, useRef, useEffect } from 'react';
import { LayoutGrid, Landmark, LayoutDashboard } from 'lucide-react';
import PeepalLeaf from './icons/PeepalLeaf';
import { apiJson } from '../api/client';

// Where the Management app lives -- overridable via env for local dev.
const MANAGEMENT_APP_URL =
  process.env.REACT_APP_MANAGEMENT_URL || 'https://bgcorp-management.onrender.com';

// Zoho/Google-style app switcher for the BG Corp Global suite. A grid button
// in the header opens a launcher; Management opens via SSO (issue a token here,
// hand it to Management's /sso/from-origin) so the user is signed in there
// automatically.
export default function AppSwitcher() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const openManagement = async () => {
    setBusy(true);
    try {
      const data = await apiJson('/api/auth/sso-issue');
      window.open(
        `${MANAGEMENT_APP_URL}/sso/from-origin?token=${encodeURIComponent(data.token)}`,
        '_blank'
      );
      setOpen(false);
    } catch (err) {
      alert(err.data?.error || 'Could not open Management right now.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        title="BG Corp Global apps"
        className="p-2 text-neutral-400 hover:text-indigo-400 transition-colors"
      >
        <LayoutGrid className="w-5 h-5" />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 bg-neutral-900 border border-white/[0.08] rounded-xl shadow-2xl z-50 overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-3 border-b border-white/[0.07] bg-white/[0.02]">
            <span className="w-7 h-7 flex items-center justify-center text-green-500">
              <PeepalLeaf className="w-5 h-5" />
            </span>
            <div>
              <div className="text-sm font-semibold text-neutral-100">BG Corp Global</div>
              <div className="text-[0.65rem] text-neutral-500">App suite</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 p-3">
            {/* Current app */}
            <div className="flex flex-col items-center text-center gap-1 p-3 rounded-lg border border-indigo-500/40 bg-white/[0.03]">
              <Landmark className="w-6 h-6 text-indigo-400" />
              <span className="text-sm font-semibold text-neutral-100">Origin</span>
              <span className="text-[0.6rem] text-neutral-500">You're here</span>
            </div>

            {/* Management (SSO) */}
            <button
              onClick={openManagement}
              disabled={busy}
              className="flex flex-col items-center text-center gap-1 p-3 rounded-lg border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.06] hover:border-white/[0.15] transition-colors disabled:opacity-60"
            >
              <LayoutDashboard className="w-6 h-6 text-emerald-400" />
              <span className="text-sm font-semibold text-neutral-100">Management</span>
              <span className="text-[0.6rem] text-neutral-500">
                {busy ? 'Opening…' : 'Tasks & time'}
              </span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
