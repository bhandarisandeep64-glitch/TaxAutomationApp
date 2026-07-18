import React, { useState, useEffect } from 'react';
import {
  CheckCircle, AlertCircle, MinusCircle, Plus, Trash2, Search, Calendar, Save, RefreshCw
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { PageHeader, Spinner, EmptyState } from '../components/ui';

export default function ComplianceTable({ user }) {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newClient, setNewClient] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [saveStatus, setSaveStatus] = useState('saved');
  const [saveError, setSaveError] = useState('');
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    setLoadError('');
    apiFetch(`/api/compliance?user_id=${user.id}`)
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok || !Array.isArray(data)) {
          throw new Error((data && data.error) || `Failed to load clients (${res.status})`);
        }
        setClients(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load data", err);
        setLoadError(err.message || 'Failed to load clients.');
        setLoading(false);
      });
  }, [user]);

  const saveData = (updatedClients) => {
    const previousClients = clients;
    setSaveStatus('saving');
    setSaveError('');
    setClients(updatedClients);

    apiFetch('/api/compliance', {
      method: 'POST',
      body: JSON.stringify({
        user_id: user.id,
        clients: updatedClients
      })
    })
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.success === false) {
          throw new Error(data.error || `Save failed (${res.status})`);
        }
        setTimeout(() => setSaveStatus('saved'), 500);
      })
      .catch((err) => {
        // Don't leave an unsaved client sitting in the table looking saved --
        // revert to the last known-good server state.
        setClients(previousClients);
        setSaveStatus('error');
        setSaveError(err.message || 'Failed to save.');
      });
  };

  const toggleStatus = (id, field) => {
    const updatedClients = clients.map(c => {
      if (c.id !== id) return c;
      const current = c[field];
      let nextStatus = 'pending';
      if (current === 'pending') nextStatus = 'done';
      else if (current === 'done') nextStatus = 'na';
      else if (current === 'na') nextStatus = 'pending';
      return { ...c, [field]: nextStatus };
    });
    saveData(updatedClients);
  };

  const addClient = () => {
    if (!newClient.trim()) return;
    const newId = clients.length > 0 ? Math.max(...clients.map(c => c.id)) + 1 : 1;
    const updatedClients = [...clients, { id: newId, name: newClient, tds: "pending", gstr1: "pending", gstr3b: "pending" }];
    saveData(updatedClients);
    setNewClient("");
    setIsAdding(false);
  };

  const deleteClient = (id) => {
    if (window.confirm("Are you sure you want to remove this client?")) {
      const updatedClients = clients.filter(c => c.id !== id);
      saveData(updatedClients);
    }
  };

  const filteredClients = clients.filter(c =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const StatusBadge = ({ status, onClick }) => {
    const styles = {
      done: "bg-emerald-500/10 text-emerald-400 border-emerald-500/25 hover:bg-emerald-500/20",
      pending: "bg-red-500/10 text-red-400 border-red-500/25 hover:bg-red-500/20",
      na: "bg-neutral-800/60 text-neutral-500 border-white/[0.06] hover:bg-neutral-800"
    };
    const icons = {
      done: <CheckCircle className="w-3 h-3" />,
      pending: <AlertCircle className="w-3 h-3" />,
      na: <MinusCircle className="w-3 h-3" />
    };
    const labels = { done: "DONE", pending: "PENDING", na: "N/A" };

    return (
      <button onClick={onClick} className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold tracking-wider transition-colors w-28 justify-center ${styles[status]}`}>
        {icons[status]} {labels[status]}
      </button>
    );
  };

  if (loading) return <div className="flex justify-center items-center h-64 text-neutral-500 gap-2"><Spinner /> Loading tracker…</div>;

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      <PageHeader
        icon={Calendar}
        eyebrow="Compliance"
        title="Compliance Tracker"
        subtitle="Monthly deadlines & client status"
        action={
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="relative flex-1 md:w-64">
              <Search className="w-4 h-4 text-neutral-600 absolute left-3 top-1/2 -translate-y-1/2" />
              <input type="text" placeholder="Search clients…" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-black/30 border border-white/[0.08] rounded-lg pl-9 pr-4 py-2.5 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors" />
            </div>
            <button onClick={() => setIsAdding(true)} className="bg-indigo-600 hover:bg-indigo-500 text-white p-2.5 rounded-lg transition-colors shadow-lg shadow-indigo-500/10 shrink-0">
              <Plus className="w-5 h-5" />
            </button>
          </div>
        }
      />

      {loadError && (
        <div className="flex items-center gap-2.5 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" /> {loadError}
        </div>
      )}

      {isAdding && (
        <div className="bg-neutral-900/60 border border-indigo-500/30 p-4 rounded-lg flex gap-4 animate-in slide-in-from-top-2">
          <input type="text" placeholder="Enter client name" autoFocus value={newClient} onChange={(e) => setNewClient(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addClient()}
            className="flex-1 bg-black/30 border border-white/[0.08] rounded-lg px-4 py-2 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors" />
          <button onClick={addClient} className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg text-sm transition-colors">Save</button>
          <button onClick={() => setIsAdding(false)} className="px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 font-medium rounded-lg text-sm transition-colors">Cancel</button>
        </div>
      )}

      <div className="rounded-lg border border-white/[0.06] bg-neutral-900/40 overflow-hidden shadow-xl shadow-black/20">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-black/20 border-b border-white/[0.06] text-xs uppercase text-neutral-500 tracking-wider">
                <th className="p-5 font-semibold">Client Name</th>
                <th className="p-5 text-center w-40">
                  <div className="flex flex-col items-center"><span>TDS Payment</span><span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 rounded mt-1">Due: 7th</span></div>
                </th>
                <th className="p-5 text-center w-40">
                  <div className="flex flex-col items-center"><span>GSTR-1</span><span className="text-[10px] text-sky-400 bg-sky-500/10 px-2 rounded mt-1">Due: 11th</span></div>
                </th>
                <th className="p-5 text-center w-40">
                  <div className="flex flex-col items-center"><span>GSTR-3B</span><span className="text-[10px] text-violet-400 bg-violet-500/10 px-2 rounded mt-1">Due: 20th</span></div>
                </th>
                <th className="p-5 w-16"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06]">
              {filteredClients.length > 0 ? (
                filteredClients.map((client) => (
                  <tr key={client.id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="p-5 font-medium text-neutral-200 text-sm border-r border-white/[0.04]">{client.name}</td>
                    <td className="p-5 text-center border-r border-white/[0.04]"><div className="flex justify-center"><StatusBadge status={client.tds} onClick={() => toggleStatus(client.id, 'tds')} /></div></td>
                    <td className="p-5 text-center border-r border-white/[0.04]"><div className="flex justify-center"><StatusBadge status={client.gstr1} onClick={() => toggleStatus(client.id, 'gstr1')} /></div></td>
                    <td className="p-5 text-center border-r border-white/[0.04]"><div className="flex justify-center"><StatusBadge status={client.gstr3b} onClick={() => toggleStatus(client.id, 'gstr3b')} /></div></td>
                    <td className="p-5 text-center">
                      <button onClick={() => deleteClient(client.id)} className="p-2 text-neutral-600 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"><Trash2 className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan="5"><EmptyState icon={Search} title="No clients found" subtitle="Add a client to start tracking their compliance deadlines." /></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex justify-end text-xs text-neutral-500 items-center gap-2">
        {saveStatus === 'saving' && <><RefreshCw className="w-3 h-3 animate-spin" /> Saving…</>}
        {saveStatus === 'saved' && <><Save className="w-3 h-3" /> Changes saved</>}
        {saveStatus === 'error' && <span className="text-red-400">Failed to save{saveError ? `: ${saveError}` : ' — check your connection.'} (change was not kept — try again)</span>}
      </div>
    </div>
  );
}
