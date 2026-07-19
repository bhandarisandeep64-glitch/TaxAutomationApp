import React, { useState } from 'react';
import {
  Upload, FileText, CheckCircle, Download, X, AlertCircle,
  Layers, Landmark, FileSpreadsheet, Zap, SlidersHorizontal
} from 'lucide-react';
import { apiFetch } from '../../api/client';
import { PageHeader, Card, Button } from '../../components/ui';

const SOURCES = [
  { key: 'file_books', label: 'As Per Books', hint: 'Your ITC register for the year', icon: FileText },
  { key: 'file_2b', label: 'As Per 2B / 8A', hint: 'GSTR-2B / 8A (invoices, CDN, amendments)', icon: Landmark },
  { key: 'file_3b', label: 'As Per 3B', hint: 'ITC actually claimed in 3B', icon: FileSpreadsheet },
];

// Control-total sources map to the engine's expected keys.
const CONTROL_KEYS = [
  { key: 'books', label: 'Books' },
  { key: 'portal', label: '2B / 8A' },
  { key: 'filed', label: '3B' },
];

export default function Gstr9Reco() {
  const [files, setFiles] = useState({ file_books: null, file_2b: null, file_3b: null });
  const [status, setStatus] = useState('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);

  const [showControls, setShowControls] = useState(false);
  const [controls, setControls] = useState({
    books: { igst: '', cgst: '', sgst: '' },
    portal: { igst: '', cgst: '', sgst: '' },
    filed: { igst: '', cgst: '', sgst: '' },
  });

  const handleFile = (key, e) => {
    if (e.target.files[0]) {
      setFiles(prev => ({ ...prev, [key]: e.target.files[0] }));
      setStatus('idle');
    }
  };

  const removeFile = (key) => {
    setFiles(prev => ({ ...prev, [key]: null }));
    setStatus('idle');
  };

  const handleControl = (source, head, value) => {
    setControls(prev => ({ ...prev, [source]: { ...prev[source], [head]: value } }));
  };

  // Only send control totals that were actually filled in (any head entered).
  const buildControlPayload = () => {
    const payload = {};
    CONTROL_KEYS.forEach(({ key }) => {
      const c = controls[key];
      if (c.igst !== '' || c.cgst !== '' || c.sgst !== '') {
        payload[key] = {
          igst: parseFloat(c.igst) || 0,
          cgst: parseFloat(c.cgst) || 0,
          sgst: parseFloat(c.sgst) || 0,
        };
      }
    });
    return Object.keys(payload).length ? payload : null;
  };

  const handleRun = async () => {
    if (!files.file_books || !files.file_2b || !files.file_3b) {
      setErrorMessage('All three files (Books, 2B/8A, 3B) are required.');
      return;
    }
    setStatus('processing');
    setErrorMessage('');
    setDownloadUrl(null);

    const formData = new FormData();
    formData.append('file_books', files.file_books);
    formData.append('file_2b', files.file_2b);
    formData.append('file_3b', files.file_3b);
    const control = buildControlPayload();
    if (control) formData.append('control_totals', JSON.stringify(control));

    try {
      const response = await apiFetch('/api/gstr9/reco', { method: 'POST', body: formData });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || 'Reconciliation failed.');
      }
      const blob = await response.blob();
      setDownloadUrl(window.URL.createObjectURL(blob));
      setStatus('success');
    } catch (e) {
      setStatus('error');
      setErrorMessage(e.message);
    }
  };

  const statusPill = {
    idle: { text: 'Ready', dot: 'bg-neutral-500', box: 'bg-neutral-900/50 border-white/[0.08] text-neutral-400' },
    processing: { text: 'Reconciling', dot: 'bg-indigo-400 animate-ping', box: 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400' },
    success: { text: 'Done', dot: 'bg-emerald-400', box: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' },
    error: { text: 'Error', dot: 'bg-red-400', box: 'bg-red-500/10 border-red-500/30 text-red-400' },
  }[status];

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-500">
      <PageHeader
        icon={Layers}
        eyebrow="GSTR-9"
        title="Annual Three-Way Reconciliation"
        subtitle="Books vs 2B/8A vs 3B — invoice-level, with cause-of-difference analysis"
        action={
          <div className={`px-4 py-1.5 rounded-full border text-xs font-medium flex items-center gap-2 ${statusPill.box}`}>
            <div className={`w-1.5 h-1.5 rounded-full ${statusPill.dot}`} />
            {statusPill.text}
          </div>
        }
      />

      {/* Source files */}
      <Card>
        <div className="flex items-center gap-2 mb-5">
          <div className="w-5 h-5 rounded flex items-center justify-center bg-indigo-500/15 text-indigo-400 text-xs font-semibold">1</div>
          <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider">Source Sheets</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {SOURCES.map(({ key, label, hint, icon: Icon }) => {
            const file = files[key];
            return (
              <div key={key} className={`relative border-2 border-dashed rounded-lg p-4 flex flex-col h-40 transition-colors ${file ? 'border-emerald-500/40 bg-emerald-500/[0.04]' : 'border-white/[0.1] bg-black/20 hover:border-indigo-500/40'}`}>
                <div className="flex items-center gap-2 mb-1">
                  <Icon className={`w-4 h-4 ${file ? 'text-emerald-400' : 'text-indigo-400'}`} />
                  <span className="text-xs font-semibold text-neutral-200">{label}</span>
                </div>
                <span className="text-[10px] text-neutral-500 leading-snug">{hint}</span>

                <div className="mt-auto">
                  {file ? (
                    <div className="flex items-center justify-between gap-2 bg-black/30 rounded-md px-2.5 py-2 border border-white/[0.06]">
                      <span className="text-[11px] text-emerald-400 font-medium truncate flex items-center gap-1.5">
                        <CheckCircle className="w-3 h-3 shrink-0" /> {file.name}
                      </span>
                      <button onClick={() => removeFile(key)} className="text-neutral-600 hover:text-red-400 shrink-0"><X className="w-3.5 h-3.5" /></button>
                    </div>
                  ) : (
                    <label className="cursor-pointer flex items-center justify-center gap-2 bg-neutral-800/60 border border-white/[0.08] rounded-md py-2 hover:bg-neutral-700/60 hover:border-indigo-500/30 transition-colors">
                      <input type="file" className="hidden" accept=".xlsx, .xls" onChange={(e) => handleFile(key, e)} />
                      <Upload className="w-3.5 h-3.5 text-neutral-400" />
                      <span className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wide">Load File</span>
                    </label>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Optional control totals */}
      <Card>
        <button onClick={() => setShowControls(v => !v)} className="w-full flex items-center gap-2 text-left">
          <div className="w-5 h-5 rounded flex items-center justify-center bg-indigo-500/15 text-indigo-400 text-xs font-semibold">2</div>
          <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider">Control Totals (optional)</h3>
          <SlidersHorizontal className="w-3.5 h-3.5 text-neutral-500 ml-1" />
          <span className="text-[10px] text-neutral-600 ml-auto">{showControls ? 'Hide' : 'Enter expected ITC totals to tie out each file'}</span>
        </button>

        {showControls && (
          <div className="mt-5 space-y-3 animate-in fade-in duration-300">
            <p className="text-[11px] text-neutral-500 leading-relaxed">
              Enter the ITC total you expect for each sheet. The report checks each uploaded file's computed total against these — so a wrong or incomplete file gets caught before you review the reconciliation.
            </p>
            <div className="grid grid-cols-[80px_1fr_1fr_1fr] gap-2 items-center">
              <div />
              <span className="text-[9px] font-mono text-neutral-500 uppercase text-center">IGST</span>
              <span className="text-[9px] font-mono text-neutral-500 uppercase text-center">CGST</span>
              <span className="text-[9px] font-mono text-neutral-500 uppercase text-center">SGST</span>
              {CONTROL_KEYS.map(({ key, label }) => (
                <React.Fragment key={key}>
                  <span className="text-[11px] font-semibold text-neutral-400">{label}</span>
                  {['igst', 'cgst', 'sgst'].map(head => (
                    <input
                      key={head}
                      type="number"
                      value={controls[key][head]}
                      onChange={(e) => handleControl(key, head, e.target.value)}
                      placeholder="0.00"
                      className="bg-black/30 border border-white/[0.08] rounded-md px-2 py-1.5 text-xs font-mono text-neutral-100 placeholder-neutral-700 focus:outline-none focus:border-indigo-500/50 transition-colors"
                    />
                  ))}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Run + result */}
      {errorMessage && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <p className="text-red-400/90 text-xs">{errorMessage}</p>
        </div>
      )}

      <div className="flex items-center justify-between gap-4">
        <p className="text-[11px] text-neutral-600 leading-relaxed max-w-md">
          Matches every invoice / credit note across all three sheets by GSTIN + Document No., classifies each difference, and tells you what's causing it.
        </p>
        <Button icon={Zap} loading={status === 'processing'} onClick={handleRun}>
          {status === 'processing' ? 'Reconciling' : 'Run Reconciliation'}
        </Button>
      </div>

      {status === 'success' && downloadUrl && (
        <a
          href={downloadUrl}
          download={`GSTR9 Reconciliation.xlsx`}
          className="group w-full flex items-center justify-between p-1 pl-4 pr-1 bg-emerald-500/5 border border-emerald-500/20 hover:border-emerald-400/40 rounded-lg transition-colors animate-in slide-in-from-bottom-4 duration-500"
        >
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Report Ready</span>
            <span className="text-xs text-neutral-300">Download the three-way reconciliation workbook</span>
          </div>
          <div className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center group-hover:scale-105 transition-transform text-neutral-950">
            <Download className="w-5 h-5" />
          </div>
        </a>
      )}
    </div>
  );
}
