import React, { useState, useEffect, useMemo } from 'react';
import { Compass, ExternalLink, Plus, Pencil, Trash2, Check, X } from 'lucide-react';
import { apiFetch, apiJson } from '../api/client';
import { PageHeader, Card, Button, Spinner, EmptyState } from '../components/ui';

function hostnameOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

export default function Hub() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);

  const [showAdd, setShowAdd] = useState(false);
  const [title, setTitle] = useState('');
  const [url, setUrl] = useState('');
  const [category, setCategory] = useState('');
  const [posting, setPosting] = useState(false);

  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [editUrl, setEditUrl] = useState('');
  const [editCategory, setEditCategory] = useState('');

  const load = () => {
    setLoading(true);
    apiFetch('/api/quick-links')
      .then(res => res.json())
      .then(data => { setGroups(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const existingCategories = useMemo(() => groups.map(g => g.category), [groups]);

  const addLink = async () => {
    if (!title.trim() || !url.trim()) return;
    setPosting(true);
    try {
      await apiJson('/api/quick-links', {
        method: 'POST',
        body: JSON.stringify({ title: title.trim(), url: url.trim(), category: category.trim() || 'General' }),
      });
      setTitle(''); setUrl(''); setCategory(''); setShowAdd(false);
      load();
    } catch (e) {
      alert(e.message || 'Failed to save link.');
    } finally {
      setPosting(false);
    }
  };

  const startEdit = (link) => {
    setEditingId(link.id);
    setEditTitle(link.title);
    setEditUrl(link.url);
    setEditCategory(link.category);
  };

  const saveEdit = async (linkId) => {
    if (!editTitle.trim() || !editUrl.trim()) return;
    try {
      await apiJson(`/api/quick-links/${linkId}`, {
        method: 'PATCH',
        body: JSON.stringify({ title: editTitle.trim(), url: editUrl.trim(), category: editCategory.trim() || 'General' }),
      });
      setEditingId(null);
      load();
    } catch (e) {
      alert(e.message || 'Failed to update link.');
    }
  };

  const removeLink = async (linkId) => {
    if (!window.confirm('Delete this link?')) return;
    try {
      await apiJson(`/api/quick-links/${linkId}`, { method: 'DELETE' });
      load();
    } catch (e) {
      alert(e.message || 'Failed to delete link.');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      <PageHeader
        icon={Compass}
        eyebrow="Workspace"
        title="Hub"
        subtitle="Your central place for Odoo, Zoho, and every other link you'd otherwise keep in a doc"
        action={
          <Button icon={Plus} onClick={() => setShowAdd(v => !v)}>
            Add Link
          </Button>
        }
      />

      {showAdd && (
        <Card>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <input
              type="text"
              placeholder="Title (e.g. Odoo)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="bg-black/30 border border-white/[0.08] rounded-lg px-3 py-2.5 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors md:col-span-1"
            />
            <input
              type="text"
              placeholder="URL"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') addLink(); }}
              className="bg-black/30 border border-white/[0.08] rounded-lg px-3 py-2.5 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors md:col-span-2"
            />
            <input
              type="text"
              placeholder="Category (e.g. Accounting Software)"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') addLink(); }}
              list="hub-categories"
              className="bg-black/30 border border-white/[0.08] rounded-lg px-3 py-2.5 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors md:col-span-1"
            />
            <datalist id="hub-categories">
              {existingCategories.map(c => <option key={c} value={c} />)}
            </datalist>
          </div>
          <div className="flex justify-end gap-2 mt-3">
            <Button variant="ghost" onClick={() => setShowAdd(false)}>Cancel</Button>
            <Button loading={posting} disabled={!title.trim() || !url.trim()} onClick={addLink}>Save</Button>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : groups.length === 0 ? (
        <Card>
          <EmptyState icon={Compass} title="No links yet" subtitle="Add Odoo, Zoho, the GST portal, or anything else you navigate to often." />
        </Card>
      ) : (
        <div className="space-y-6">
          {groups.map(({ category: cat, links }) => (
            <div key={cat}>
              <p className="text-[11px] font-semibold text-neutral-500 uppercase tracking-[0.15em] mb-3">{cat}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {links.map((link) => (
                  <Card key={link.id} className="group relative">
                    {editingId === link.id ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="w-full bg-black/30 border border-indigo-500/40 rounded-lg px-2.5 py-1.5 text-sm text-neutral-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        />
                        <input
                          type="text"
                          value={editUrl}
                          onChange={(e) => setEditUrl(e.target.value)}
                          className="w-full bg-black/30 border border-indigo-500/40 rounded-lg px-2.5 py-1.5 text-xs text-neutral-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        />
                        <input
                          type="text"
                          value={editCategory}
                          onChange={(e) => setEditCategory(e.target.value)}
                          list="hub-categories"
                          className="w-full bg-black/30 border border-indigo-500/40 rounded-lg px-2.5 py-1.5 text-xs text-neutral-300 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                        />
                        <div className="flex gap-2 justify-end">
                          <button onClick={() => setEditingId(null)} className="p-1.5 text-neutral-500 hover:text-neutral-200 rounded-md hover:bg-white/[0.06]"><X className="w-4 h-4" /></button>
                          <button onClick={() => saveEdit(link.id)} className="p-1.5 text-emerald-400 hover:bg-emerald-500/10 rounded-md"><Check className="w-4 h-4" /></button>
                        </div>
                      </div>
                    ) : (
                      <a href={link.url} target="_blank" rel="noopener noreferrer" className="block">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium text-neutral-100 group-hover:text-indigo-400 transition-colors">{link.title}</p>
                          <ExternalLink className="w-3.5 h-3.5 text-neutral-600 shrink-0 mt-0.5" />
                        </div>
                        <p className="text-xs text-neutral-600 mt-1 truncate">{hostnameOf(link.url)}</p>
                      </a>
                    )}

                    {editingId !== link.id && (
                      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-neutral-950/80 rounded-md">
                        <button onClick={(e) => { e.preventDefault(); startEdit(link); }} className="p-1.5 text-neutral-500 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-md"><Pencil className="w-3.5 h-3.5" /></button>
                        <button onClick={(e) => { e.preventDefault(); removeLink(link.id); }} className="p-1.5 text-neutral-500 hover:text-red-400 hover:bg-red-500/10 rounded-md"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
