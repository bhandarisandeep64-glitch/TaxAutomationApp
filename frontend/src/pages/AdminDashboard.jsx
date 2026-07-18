import React, { useState, useEffect } from 'react';
import {
  Users, Shield, Lock, Plus, RefreshCw, Activity, Trash2, ShieldAlert
} from 'lucide-react';
import { apiJson } from '../api/client';
import { PageHeader, Card, Button, Badge, StatCard } from '../components/ui';

export default function AdminDashboard({ currentUser }) {
  const [stats, setStats] = useState({ teamMembers: 0, restrictedAccounts: 0, systemStatus: 'Optimal' });
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isAddingUser, setIsAddingUser] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', password: '', name: '', role: 'user', status: 'Active', restrictedModules: [] });

  const fetchAllData = () => {
    setLoading(true);
    apiJson('/api/auth/users')
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
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => { fetchAllData(); }, []);

  const toggleModuleAccess = (userId, moduleKey) => {
    const target = users.find(u => u.id === userId);
    if (!target) return;
    const currentRestricted = target.restrictedModules || [];
    const newRestricted = currentRestricted.includes(moduleKey)
      ? currentRestricted.filter(m => m !== moduleKey)
      : [...currentRestricted, moduleKey];

    apiJson(`/api/auth/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify({ restrictedModules: newRestricted })
    }).then(fetchAllData);
  };

  const toggleUserStatus = (id) => {
    const target = users.find(u => u.id === id);
    if (!target) return;
    apiJson(`/api/auth/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: target.status === 'Active' ? 'Restricted' : 'Active' })
    }).then(fetchAllData);
  };

  const deleteUser = (id) => {
    if (window.confirm("Remove user?")) {
      apiJson(`/api/auth/users/${id}`, { method: 'DELETE' }).then(fetchAllData);
    }
  };

  const handleAddUser = () => {
    if (!newUser.username || !newUser.password) return;
    apiJson('/api/auth/users', {
      method: 'POST',
      body: JSON.stringify(newUser)
    }).then(() => {
      fetchAllData();
      setIsAddingUser(false);
      setNewUser({ username: '', password: '', name: '', role: 'user', status: 'Active', restrictedModules: [] });
    }).catch(err => alert(err.message || 'Failed to create user'));
  };

  const toggleNewUserPermission = (mod) => {
    setNewUser(prev => {
      const list = prev.restrictedModules;
      return list.includes(mod) ? { ...prev, restrictedModules: list.filter(m => m !== mod) } : { ...prev, restrictedModules: [...list, mod] };
    });
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">

      <PageHeader
        icon={Shield}
        eyebrow="Overview"
        title="Command Center"
        subtitle="System overview & user management"
        action={
          <Button icon={Plus} onClick={() => setIsAddingUser(true)}>Add Team Member</Button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard label="Team Members" value={stats.teamMembers} icon={Users} sub="Active accounts" />
        <StatCard label="Restricted Accounts" value={stats.restrictedAccounts} icon={Lock} sub="Access revoked" />
        <StatCard label="System Status" value={stats.systemStatus} icon={Activity} sub="All systems nominal" />
      </div>

      {isAddingUser && (
        <Card className="border-indigo-500/30 animate-in slide-in-from-top-4">
          <h3 className="text-neutral-100 font-semibold mb-4 text-sm">Create New Account</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <input type="text" placeholder="Full Name" className="bg-black/30 border border-white/[0.08] rounded-lg px-3 py-2.5 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors" value={newUser.name} onChange={e => setNewUser({ ...newUser, name: e.target.value })} />
            <input type="text" placeholder="Username" className="bg-black/30 border border-white/[0.08] rounded-lg px-3 py-2.5 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors" value={newUser.username} onChange={e => setNewUser({ ...newUser, username: e.target.value })} />
            <input type="password" placeholder="Password" className="bg-black/30 border border-white/[0.08] rounded-lg px-3 py-2.5 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors" value={newUser.password} onChange={e => setNewUser({ ...newUser, password: e.target.value })} />
          </div>
          <div className="mb-5 flex gap-6">
            <label className="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer"><input type="checkbox" checked={!newUser.restrictedModules.includes('direct_tax')} onChange={() => toggleNewUserPermission('direct_tax')} className="accent-indigo-500" /> Direct Tax</label>
            <label className="flex items-center gap-2 text-sm text-neutral-400 cursor-pointer"><input type="checkbox" checked={!newUser.restrictedModules.includes('indirect_tax')} onChange={() => toggleNewUserPermission('indirect_tax')} className="accent-indigo-500" /> Indirect Tax</label>
          </div>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setIsAddingUser(false)}>Cancel</Button>
            <Button onClick={handleAddUser}>Create User</Button>
          </div>
        </Card>
      )}

      <Card padded={false}>
        <div className="p-6 border-b border-white/[0.06] flex justify-between items-center">
          <h3 className="text-sm font-semibold text-neutral-100 flex items-center gap-2 uppercase tracking-wide"><ShieldAlert className="w-4 h-4 text-indigo-400" /> Team Access</h3>
          <button onClick={fetchAllData} className="text-neutral-500 hover:text-neutral-200 transition-colors"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /></button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-black/20 text-neutral-500 text-xs uppercase tracking-wider">
              <tr><th className="p-5 font-medium">Name</th><th className="p-5 font-medium">Username</th><th className="p-5 font-medium">Module Access</th><th className="p-5 font-medium">Status</th><th className="p-5 text-right font-medium">Actions</th></tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06]">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-white/[0.02] transition-colors">
                  <td className="p-5 font-medium text-neutral-200">{u.name}</td>
                  <td className="p-5 text-neutral-500 font-mono text-xs">{u.username}</td>
                  <td className="p-5">
                    <div className="flex gap-2">
                      <button
                        onClick={() => toggleModuleAccess(u.id, 'direct_tax')}
                        className={`px-2.5 py-1 rounded-md text-xs border transition-colors ${
                          u.restrictedModules && u.restrictedModules.includes('direct_tax')
                            ? 'bg-red-500/5 text-red-500/70 border-red-500/20 line-through hover:opacity-100'
                            : 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20 hover:bg-indigo-500/20'
                        }`}
                      >
                        Direct Tax
                      </button>
                      <button
                        onClick={() => toggleModuleAccess(u.id, 'indirect_tax')}
                        className={`px-2.5 py-1 rounded-md text-xs border transition-colors ${
                          u.restrictedModules && u.restrictedModules.includes('indirect_tax')
                            ? 'bg-red-500/5 text-red-500/70 border-red-500/20 line-through hover:opacity-100'
                            : 'bg-sky-500/10 text-sky-400 border-sky-500/20 hover:bg-sky-500/20'
                        }`}
                      >
                        Indirect Tax
                      </button>
                    </div>
                  </td>
                  <td className="p-5"><Badge status={u.status === 'Active' ? 'success' : 'error'}>{u.status}</Badge></td>
                  <td className="p-5 text-right flex justify-end gap-1.5">
                    <button onClick={() => toggleUserStatus(u.id)} className="p-2 text-neutral-500 hover:text-neutral-100 hover:bg-white/[0.06] rounded-lg transition-colors"><Lock className="w-4 h-4" /></button>
                    <button onClick={() => deleteUser(u.id)} className="p-2 text-neutral-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
