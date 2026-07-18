import React, { useState, useEffect, useMemo } from 'react';
import { StickyNote, Search, Pencil, Trash2, Check, X, Send } from 'lucide-react';
import { apiFetch, apiJson } from '../api/client';
import { PageHeader, Card, Button, Spinner, EmptyState } from '../components/ui';

export default function Notes({ user }) {
  const [clients, setClients] = useState([]);
  const [clientsLoading, setClientsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedClient, setSelectedClient] = useState(null);

  const [notes, setNotes] = useState([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [newNoteText, setNewNoteText] = useState('');
  const [posting, setPosting] = useState(false);

  const [editingId, setEditingId] = useState(null);
  const [editingText, setEditingText] = useState('');

  useEffect(() => {
    if (!user) return;
    setClientsLoading(true);
    apiFetch(`/api/compliance?user_id=${user.id}`)
      .then(res => res.json())
      .then(data => {
        setClients(data);
        setClientsLoading(false);
      })
      .catch(() => setClientsLoading(false));
  }, [user]);

  const loadNotes = (clientName) => {
    setNotesLoading(true);
    apiFetch(`/api/notes?client_name=${encodeURIComponent(clientName)}`)
      .then(res => res.json())
      .then(data => {
        setNotes(data);
        setNotesLoading(false);
      })
      .catch(() => setNotesLoading(false));
  };

  const selectClient = (client) => {
    setSelectedClient(client);
    setEditingId(null);
    setNewNoteText('');
    loadNotes(client.name);
  };

  const addNote = async () => {
    if (!newNoteText.trim() || !selectedClient) return;
    setPosting(true);
    try {
      await apiJson('/api/notes', {
        method: 'POST',
        body: JSON.stringify({ client_name: selectedClient.name, content: newNoteText.trim() }),
      });
      setNewNoteText('');
      loadNotes(selectedClient.name);
    } catch (e) {
      alert(e.message || 'Failed to save note.');
    } finally {
      setPosting(false);
    }
  };

  const startEdit = (note) => {
    setEditingId(note.id);
    setEditingText(note.content);
  };

  const saveEdit = async (noteId) => {
    if (!editingText.trim()) return;
    try {
      await apiJson(`/api/notes/${noteId}`, {
        method: 'PATCH',
        body: JSON.stringify({ content: editingText.trim() }),
      });
      setEditingId(null);
      loadNotes(selectedClient.name);
    } catch (e) {
      alert(e.message || 'Failed to update note.');
    }
  };

  const removeNote = async (noteId) => {
    if (!window.confirm('Delete this note? This cannot be undone.')) return;
    try {
      await apiJson(`/api/notes/${noteId}`, { method: 'DELETE' });
      loadNotes(selectedClient.name);
    } catch (e) {
      alert(e.message || 'Failed to delete note.');
    }
  };

  const filteredClients = useMemo(
    () => clients.filter(c => c.name.toLowerCase().includes(searchTerm.toLowerCase())),
    [clients, searchTerm]
  );

  const formatTimestamp = (iso) => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <PageHeader icon={StickyNote} eyebrow="Workspace" title="Notes" subtitle="Client-wise working notes" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Client list */}
        <Card padded={false} className="lg:col-span-1 flex flex-col max-h-[70vh]">
          <div className="p-4 border-b border-white/[0.07]">
            <div className="relative">
              <Search className="w-4 h-4 text-neutral-600 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search clients…"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-black/30 border border-white/[0.08] rounded-lg pl-9 pr-3 py-2 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {clientsLoading ? (
              <div className="flex justify-center py-10"><Spinner /></div>
            ) : filteredClients.length === 0 ? (
              <EmptyState icon={Search} title="No clients found" subtitle="Add clients from the Compliance Tracker first." />
            ) : (
              filteredClients.map((client) => (
                <button
                  key={client.id}
                  onClick={() => selectClient(client)}
                  className={`w-full text-left px-4 py-3 border-b border-white/[0.04] transition-colors text-sm font-medium ${
                    selectedClient?.id === client.id ? 'bg-indigo-500/10 text-indigo-400' : 'text-neutral-300 hover:bg-white/[0.03]'
                  }`}
                >
                  {client.name}
                </button>
              ))
            )}
          </div>
        </Card>

        {/* Notes panel */}
        <Card padded={false} className="lg:col-span-2 flex flex-col max-h-[70vh]">
          {!selectedClient ? (
            <EmptyState icon={StickyNote} title="Select a client" subtitle="Pick a client from the list to view or add notes." />
          ) : (
            <>
              <div className="p-4 border-b border-white/[0.07]">
                <h3 className="text-sm font-semibold text-neutral-100">{selectedClient.name}</h3>
                <div className="mt-3 flex gap-2">
                  <textarea
                    value={newNoteText}
                    onChange={(e) => setNewNoteText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) addNote(); }}
                    placeholder="Add a dated note… (Ctrl+Enter to save)"
                    className="flex-1 h-16 bg-black/30 border border-white/[0.08] rounded-lg p-3 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 resize-none transition-colors"
                  />
                  <Button icon={Send} loading={posting} disabled={!newNoteText.trim()} onClick={addNote} className="self-end">
                    Add
                  </Button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
                {notesLoading ? (
                  <div className="flex justify-center py-10"><Spinner /></div>
                ) : notes.length === 0 ? (
                  <EmptyState icon={StickyNote} title="No notes yet" subtitle="Add the first note for this client above." />
                ) : (
                  notes.map((note) => (
                    <div key={note.id} className="p-4 rounded-lg bg-black/20 border border-white/[0.06] group">
                      {editingId === note.id ? (
                        <div className="space-y-2">
                          <textarea
                            value={editingText}
                            onChange={(e) => setEditingText(e.target.value)}
                            className="w-full h-20 bg-black/30 border border-indigo-500/40 rounded-lg p-2.5 text-sm text-neutral-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 resize-none transition-colors"
                          />
                          <div className="flex gap-2 justify-end">
                            <button onClick={() => setEditingId(null)} className="p-1.5 text-neutral-500 hover:text-neutral-200 rounded-md hover:bg-white/[0.06]"><X className="w-4 h-4" /></button>
                            <button onClick={() => saveEdit(note.id)} className="p-1.5 text-emerald-400 hover:bg-emerald-500/10 rounded-md"><Check className="w-4 h-4" /></button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-sm text-neutral-200 leading-relaxed whitespace-pre-wrap">{note.content}</p>
                            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                              <button onClick={() => startEdit(note)} className="p-1.5 text-neutral-500 hover:text-indigo-400 hover:bg-indigo-500/10 rounded-md"><Pencil className="w-3.5 h-3.5" /></button>
                              <button onClick={() => removeNote(note.id)} className="p-1.5 text-neutral-500 hover:text-red-400 hover:bg-red-500/10 rounded-md"><Trash2 className="w-3.5 h-3.5" /></button>
                            </div>
                          </div>
                          <p className="text-[11px] text-neutral-600 mt-2">
                            {formatTimestamp(note.createdAt)}
                            {note.updatedAt !== note.createdAt && ' · edited'}
                          </p>
                        </>
                      )}
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
