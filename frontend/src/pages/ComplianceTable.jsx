import React, { useState, useEffect } from 'react';
import { 
  CheckCircle, AlertCircle, MinusCircle, Plus, Trash2, Search, Calendar, Save, RefreshCw
} from 'lucide-react';
import { THEME } from '../constants/theme';

export default function ComplianceTable({ user }) { // Receive user prop
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newClient, setNewClient] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [saveStatus, setSaveStatus] = useState('saved');

  // --- API CALLS ---
  
  // Load Data specific to this User
  useEffect(() => {
    if (!user) return;
    
    setLoading(true);
    // Pass user_id in query params
    fetch(`https://taxautomationapp.onrender.com/api/compliance?user_id=${user.id}`)
      .then(res => res.json())
      .then(data => {
        setClients(data);
        setLoading(false);
      })
      .catch(err => console.error("Failed to load data", err));
  }, [user]); // Re-run if user changes

  // Save Data specific to this User
  const saveData = (updatedClients) => {
    setSaveStatus('saving');
    setClients(updatedClients);
    
    fetch('https://taxautomationapp.onrender.com/api/compliance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // Send user_id in body
      body: JSON.stringify({ 
          user_id: user.id,
          clients: updatedClients 
      })
    })
    .then(res => res.json())
    .then(() => setTimeout(() => setSaveStatus('saved'), 500))
    .catch(() => setSaveStatus('error'));
  };

  // --- HELPERS ---
  
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
      done: "bg-green-500/10 text-green-500 border-green-500/30 hover:bg-green-500/20",
      pending: "bg-red-500/10 text-red-500 border-red-500/30 hover:bg-red-500/20",
      na: "bg-slate-700/30 text-slate-500 border-slate-700 hover:bg-slate-700/50"
    };
    const icons = {
      done: <CheckCircle className="w-3 h-3" />,
      pending: <AlertCircle className="w-3 h-3" />,
      na: <MinusCircle className="w-3 h-3" />
    };
    const labels = { done: "DONE", pending: "PENDING", na: "N/A" };

    return (
      <button onClick={onClick} className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold tracking-wider transition-all w-28 justify-center ${styles[status]}`}>
        {icons[status]} {labels[status]}
      </button>
    );
  };

  if (loading) return <div className="flex justify-center items-center h-64 text-slate-500"><RefreshCw className="w-6 h-6 animate-spin mr-2"/> Loading Tracker...</div>;

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-end border-b border-slate-800 pb-6 gap-4">
        <div className="flex items-center gap-4">
            <div className={`p-3 rounded-xl bg-gradient-to-br from-slate-800 to-black border border-slate-700 shadow-lg`}>
                <Calendar className={`w-8 h-8 ${THEME.accent}`} />
            </div>
            <div>
                <h2 className="text-3xl font-bold text-white tracking-tight">Compliance Tracker</h2>
                <p className="text-slate-400 mt-1">Monthly Deadlines & Client Status</p>
            </div>
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="relative flex-1 md:w-64">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input type="text" placeholder="Search Clients..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:border-amber-500 outline-none transition-all" />
            </div>
            <button onClick={() => setIsAdding(true)} className="bg-amber-600 hover:bg-amber-500 text-slate-900 p-2.5 rounded-xl transition-colors shadow-lg shadow-amber-900/20">
                <Plus className="w-5 h-5" />
            </button>
        </div>
      </div>

      {/* Add Client Input */}
      {isAdding && (
          <div className="bg-slate-900/50 border border-amber-500/30 p-4 rounded-xl flex gap-4 animate-in slide-in-from-top-2">
              <input type="text" placeholder="Enter Client Name" autoFocus value={newClient} onChange={(e) => setNewClient(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addClient()}
                  className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-4 py-2 text-white focus:border-amber-500 outline-none" />
              <button onClick={addClient} className="px-6 py-2 bg-green-600 hover:bg-green-500 text-white font-bold rounded-lg text-sm">Save</button>
              <button onClick={() => setIsAdding(false)} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-lg text-sm">Cancel</button>
          </div>
      )}

      {/* Main Table */}
      <div className={`rounded-2xl border ${THEME.border} bg-slate-900/30 overflow-hidden shadow-xl`}>
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="bg-slate-950 border-b border-slate-800 text-xs uppercase text-slate-400 tracking-wider">
                        <th className="p-5 font-bold">Client Name</th>
                        <th className="p-5 text-center w-40">
                            <div className="flex flex-col items-center"><span>TDS Payment</span><span className="text-[10px] text-amber-500 bg-amber-900/20 px-2 rounded mt-1">Due: 7th</span></div>
                        </th>
                        <th className="p-5 text-center w-40">
                            <div className="flex flex-col items-center"><span>GSTR-1</span><span className="text-[10px] text-purple-400 bg-purple-900/20 px-2 rounded mt-1">Due: 11th</span></div>
                        </th>
                        <th className="p-5 text-center w-40">
                            <div className="flex flex-col items-center"><span>GSTR-3B</span><span className="text-[10px] text-blue-400 bg-blue-900/20 px-2 rounded mt-1">Due: 20th</span></div>
                        </th>
                        <th className="p-5 w-16"></th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                    {filteredClients.length > 0 ? (
                        filteredClients.map((client) => (
                            <tr key={client.id} className="hover:bg-slate-800/30 transition-colors group">
                                <td className="p-5 font-medium text-slate-200 text-sm border-r border-slate-800/50">{client.name}</td>
                                <td className="p-5 text-center border-r border-slate-800/50"><div className="flex justify-center"><StatusBadge status={client.tds} onClick={() => toggleStatus(client.id, 'tds')} /></div></td>
                                <td className="p-5 text-center border-r border-slate-800/50"><div className="flex justify-center"><StatusBadge status={client.gstr1} onClick={() => toggleStatus(client.id, 'gstr1')} /></div></td>
                                <td className="p-5 text-center border-r border-slate-800/50"><div className="flex justify-center"><StatusBadge status={client.gstr3b} onClick={() => toggleStatus(client.id, 'gstr3b')} /></div></td>
                                <td className="p-5 text-center">
                                    <button onClick={() => deleteClient(client.id)} className="p-2 text-slate-600 hover:text-red-400 hover:bg-red-900/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"><Trash2 className="w-4 h-4" /></button>
                                </td>
                            </tr>
                        ))
                    ) : (
                        <tr><td colSpan="5" className="p-10 text-center text-slate-500">No clients found for this user.</td></tr>
                    )}
                </tbody>
            </table>
        </div>
      </div>
      
      <div className="flex justify-end text-xs text-slate-500 items-center gap-2">
          {saveStatus === 'saving' && <><RefreshCw className="w-3 h-3 animate-spin"/> Saving...</>}
          {saveStatus === 'saved' && <><Save className="w-3 h-3"/> Changes Saved to Database</>}
          {saveStatus === 'error' && <span className="text-red-500">Failed to Save! Check Backend.</span>}
      </div>
    </div>
  );
}