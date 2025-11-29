import React, { useState, useEffect } from 'react';
import { 
  Users, Shield, AlertTriangle, CheckCircle, Search, Lock, Unlock, Plus, X, Save, RefreshCw, Activity, Trash2
} from 'lucide-react';
import { THEME } from '../constants/theme';

export default function AdminDashboard({ currentUser }) {
  const [stats, setStats] = useState({ teamMembers: 0, restrictedAccounts: 0, systemStatus: 'Optimal' });
  const [users, setUsers] = useState([]); 
  const [loading, setLoading] = useState(true);
  const [isAddingUser, setIsAddingUser] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', password: '', name: '', role: 'user', status: 'Active', restrictedModules: [] });
  
  const fetchAllData = () => {
    setLoading(true);
    fetch('http://127.0.0.1:5000/api/auth/users')
      .then(res => res.json())
      .then(userData => {
        const safeUserData = Array.isArray(userData) ? userData : [];
        const employeeData = safeUserData.filter(u => u.role !== 'admin');
        setUsers(employeeData);
        
        setStats({ 
            teamMembers: employeeData.length, 
            restrictedAccounts: employeeData.filter(u => u.status === 'Restricted').length, 
            systemStatus: 'Online' 
        });
        setLoading(false);
      });
  };

  useEffect(() => { fetchAllData(); }, []);

  const saveUsersToBackend = (updatedUsers) => {
    // First get fresh master list, then merge updates
    fetch('http://127.0.0.1:5000/api/auth/users')
    .then(res => res.json())
    .then(allUsers => {
        const masterList = allUsers.map(serverUser => {
            const localMatch = updatedUsers.find(u => u.id === serverUser.id);
            return localMatch || serverUser;
        });
        // Add new if missing
        updatedUsers.forEach(localUser => {
            if (!masterList.find(u => u.id === localUser.id)) masterList.push(localUser);
        });

        fetch('http://127.0.0.1:5000/api/auth/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(masterList)
        }).then(() => fetchAllData());
    });
  };

  // --- PERMISSION TOGGLE ---
  const toggleModuleAccess = (userId, moduleKey) => {
      const updated = users.map(u => {
          if (u.id !== userId) return u;
          const currentRestricted = u.restrictedModules || [];
          let newRestricted;
          
          if (currentRestricted.includes(moduleKey)) {
              // Un-restrict (Remove from list)
              newRestricted = currentRestricted.filter(m => m !== moduleKey);
          } else {
              // Restrict (Add to list)
              newRestricted = [...currentRestricted, moduleKey];
          }
          return { ...u, restrictedModules: newRestricted };
      });
      setUsers(updated);
      saveUsersToBackend(updated);
  };

  const toggleUserStatus = (id) => {
    const updated = users.map(u => u.id === id ? { ...u, status: u.status === 'Active' ? 'Restricted' : 'Active' } : u);
    setUsers(updated);
    saveUsersToBackend(updated);
  };

  const deleteUser = (id) => {
      if (window.confirm("Remove user?")) {
          setUsers(prev => prev.filter(u => u.id !== id));
          fetch('http://127.0.0.1:5000/api/auth/users')
            .then(res => res.json())
            .then(allUsers => {
                const remaining = allUsers.filter(u => u.id !== id);
                fetch('http://127.0.0.1:5000/api/auth/users', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(remaining)
                }).then(() => fetchAllData());
            });
      }
  };

  const handleAddUser = () => {
    if (!newUser.username || !newUser.password) return;
    const id = Date.now(); 
    const updated = [...users, { ...newUser, id }];
    setUsers(updated);
    saveUsersToBackend(updated);
    setIsAddingUser(false);
    setNewUser({ username: '', password: '', name: '', role: 'user', status: 'Active', restrictedModules: [] });
  };

  const toggleNewUserPermission = (mod) => {
      setNewUser(prev => {
          const list = prev.restrictedModules;
          return list.includes(mod) ? { ...prev, restrictedModules: list.filter(m => m !== mod) } : { ...prev, restrictedModules: [...list, mod] };
      });
  };

  // --- WIDGETS ---
  const StatCard = ({ title, value, icon: Icon, color, sub }) => (
    <div className={`p-6 rounded-2xl border border-slate-800 bg-slate-900/50 shadow-xl relative overflow-hidden group`}>
      <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-${color}-500`}><Icon className="w-24 h-24" /></div>
      <div className="relative z-10">
        <div className={`w-12 h-12 rounded-xl bg-${color}-900/20 flex items-center justify-center text-${color}-500 mb-4 border border-${color}-500/20`}><Icon className="w-6 h-6" /></div>
        <h3 className="text-3xl font-bold text-white mb-1">{value}</h3>
        <p className="text-sm text-slate-400 font-medium uppercase tracking-wider">{title}</p>
        <p className="text-xs text-slate-500 mt-2">{sub}</p>
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      <div className="flex justify-between items-end">
        <div><h1 className="text-3xl font-bold text-white tracking-tight">Command Center</h1><p className="text-slate-400 mt-1">System Overview & User Management</p></div>
        <button onClick={() => setIsAddingUser(true)} className="bg-amber-600 hover:bg-amber-500 text-slate-900 px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 transition-colors shadow-lg shadow-amber-900/20"><Plus className="w-4 h-4" /> Add Team Member</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard title="Team Members" value={stats.teamMembers} icon={Users} color="blue" sub="Active Accounts" />
        <StatCard title="Restricted Accounts" value={stats.restrictedAccounts} icon={Lock} color="red" sub="Access Revoked" />
        <StatCard title="System Status" value={stats.systemStatus} icon={Activity} color="emerald" sub="All Systems Nominal" />
      </div>

      {isAddingUser && (
          <div className="bg-slate-900 border border-amber-500/50 p-6 rounded-xl animate-in slide-in-from-top-4 mb-6">
              <h3 className="text-white font-bold mb-4">Create New Account</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  <input type="text" placeholder="Full Name" className="bg-slate-950 border border-slate-700 rounded p-2 text-white focus:border-amber-500 outline-none" value={newUser.name} onChange={e => setNewUser({...newUser, name: e.target.value})} />
                  <input type="text" placeholder="Username" className="bg-slate-950 border border-slate-700 rounded p-2 text-white focus:border-amber-500 outline-none" value={newUser.username} onChange={e => setNewUser({...newUser, username: e.target.value})} />
                  <input type="password" placeholder="Password" className="bg-slate-950 border border-slate-700 rounded p-2 text-white focus:border-amber-500 outline-none" value={newUser.password} onChange={e => setNewUser({...newUser, password: e.target.value})} />
              </div>
              <div className="mb-4 flex gap-6">
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer"><input type="checkbox" checked={!newUser.restrictedModules.includes('direct_tax')} onChange={() => toggleNewUserPermission('direct_tax')} className="accent-amber-600"/> Direct Tax</label>
                  <label className="flex items-center gap-2 text-slate-300 cursor-pointer"><input type="checkbox" checked={!newUser.restrictedModules.includes('indirect_tax')} onChange={() => toggleNewUserPermission('indirect_tax')} className="accent-amber-600"/> Indirect Tax</label>
              </div>
              <div className="flex gap-2 justify-end">
                  <button onClick={() => setIsAddingUser(false)} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded font-medium">Cancel</button>
                  <button onClick={handleAddUser} className="px-6 py-2 bg-green-600 hover:bg-green-500 text-white rounded font-bold">Create User</button>
              </div>
          </div>
      )}

      <div className={`rounded-2xl border ${THEME.border} bg-slate-900/30 overflow-hidden shadow-xl`}>
        <div className="p-6 border-b border-slate-800 flex justify-between items-center">
            <h3 className="text-lg font-bold text-white flex items-center gap-2"><Shield className="w-5 h-5 text-purple-500" /> Team Access</h3>
            <button onClick={fetchAllData} className="text-slate-500 hover:text-white"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /></button>
        </div>
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead className="bg-slate-950 text-slate-400 text-xs uppercase">
                    <tr><th className="p-5">Name</th><th className="p-5">Username</th><th className="p-5">Module Access (Click to Toggle)</th><th className="p-5">Status</th><th className="p-5 text-right">Actions</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                    {users.map((u) => (
                        <tr key={u.id} className="hover:bg-slate-800/30 transition-colors">
                            <td className="p-5 font-medium text-slate-200">{u.name}</td>
                            <td className="p-5 text-slate-400 font-mono text-xs">{u.username}</td>
                            <td className="p-5">
                                <div className="flex gap-2">
                                    {/* Direct Tax Badge */}
                                    <button 
                                        onClick={() => toggleModuleAccess(u.id, 'direct_tax')}
                                        className={`px-2 py-1 rounded text-xs border transition-all ${
                                            u.restrictedModules && u.restrictedModules.includes('direct_tax') 
                                            ? 'bg-red-900/20 text-red-500 border-red-900/50 line-through opacity-70 hover:opacity-100' 
                                            : 'bg-blue-900/30 text-blue-400 border-blue-900 hover:bg-blue-900/50'
                                        }`}
                                    >
                                        Direct Tax
                                    </button>
                                    
                                    {/* Indirect Tax Badge */}
                                    <button 
                                        onClick={() => toggleModuleAccess(u.id, 'indirect_tax')}
                                        className={`px-2 py-1 rounded text-xs border transition-all ${
                                            u.restrictedModules && u.restrictedModules.includes('indirect_tax') 
                                            ? 'bg-red-900/20 text-red-500 border-red-900/50 line-through opacity-70 hover:opacity-100' 
                                            : 'bg-purple-900/30 text-purple-400 border-purple-900 hover:bg-purple-900/50'
                                        }`}
                                    >
                                        Indirect Tax
                                    </button>
                                </div>
                            </td>
                            <td className="p-5"><span className={`px-2 py-1 rounded text-xs border ${u.status === 'Active' ? 'bg-green-900/20 text-green-400 border-green-900' : 'bg-red-900/20 text-red-400 border-red-900'}`}>{u.status}</span></td>
                            <td className="p-5 text-right flex justify-end gap-2">
                                <button onClick={() => toggleUserStatus(u.id)} className="p-2 text-slate-500 hover:text-white hover:bg-slate-700 rounded-lg"><Lock className="w-4 h-4"/></button>
                                <button onClick={() => deleteUser(u.id)} className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-900/10 rounded-lg"><Trash2 className="w-4 h-4"/></button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
      </div>
    </div>
  );
}