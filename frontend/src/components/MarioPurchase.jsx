import React, { useState } from 'react';
import { FileText, CheckCircle, Download, X, Plus, ShoppingCart, Zap } from 'lucide-react';
import { apiFetch } from '../api/client';
import { PageHeader, Card, Button } from './ui';

export default function MarioPurchase() {
  const [files, setFiles] = useState({
    file_reg_cgst: null,
    file_reg_igst: null,
    file_rcm_cgst: null,
    file_rcm_igst: null,
    file_import_cgst: null,
    file_import_igst: null,
  });

  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [blobUrl, setBlobUrl] = useState(null);

  const handleFileChange = (e) => {
    const { name, files: selectedFiles } = e.target;
    if (selectedFiles && selectedFiles.length > 0) {
      setFiles((prev) => ({ ...prev, [name]: selectedFiles[0] }));
      setStatus('idle');
      setMessage('');
      setBlobUrl(null);
    }
  };

  const handleRemoveFile = (name) => {
    setFiles((prev) => ({ ...prev, [name]: null }));
    setStatus('idle');
  };

  const handleRunAutomation = async () => {
    const hasFiles = Object.values(files).some(file => file !== null);
    if (!hasFiles) {
      setStatus('error');
      setMessage('Please upload at least one file!');
      return;
    }

    setStatus('processing');
    setMessage('');

    const formData = new FormData();
    for (const key in files) {
      if (files[key]) formData.append(key, files[key]);
    }

    try {
      const response = await apiFetch('/api/mario/purchase', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Server Error. Please try again.');
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      setBlobUrl(downloadUrl);

      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = 'Mario_Combined_Purchase.xlsx';
      document.body.appendChild(link);
      link.click();
      link.remove();

      setStatus('success');
      setMessage('File processed and downloaded successfully!');
    } catch (error) {
      setStatus('error');
      setMessage(error.message || 'Failed to connect to backend.');
    }
  };

  const renderFileSlot = (label, name) => {
    const file = files[name];
    return (
      <div className="relative p-4 rounded-xl border border-dashed border-white/[0.1] hover:border-amber-500/40 bg-black/20 transition-colors flex flex-col justify-between h-full">
        <label className="text-xs font-semibold text-neutral-400 mb-3 block uppercase tracking-wider">{label}</label>

        {file ? (
          <div className="flex items-center justify-between bg-black/30 p-2.5 rounded-lg border border-white/[0.08] animate-in zoom-in-95">
            <div className="flex items-center gap-2 overflow-hidden">
              <FileText className="w-4 h-4 text-amber-400 flex-shrink-0" />
              <span className="text-xs text-neutral-300 truncate">{file.name}</span>
            </div>
            <button onClick={() => handleRemoveFile(name)} className="text-neutral-500 hover:text-red-400 ml-2 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="relative mt-auto">
            <input type="file" id={name} name={name} className="hidden" accept=".xlsx, .xls" onChange={handleFileChange} />
            <label
              htmlFor={name}
              className="cursor-pointer flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-black/30 border border-white/[0.08] hover:bg-white/[0.04] hover:border-white/[0.14] text-neutral-500 hover:text-neutral-200 transition-colors text-xs font-medium"
            >
              <Plus className="w-3 h-3" /> Add File
            </label>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      <PageHeader icon={ShoppingCart} eyebrow="Mario" title="Purchase Converter" subtitle="Odoo" />

      <Card>
        <div className="flex flex-col lg:flex-row gap-8 items-stretch">
          <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-neutral-200 border-b border-white/[0.06] pb-2">Regular Bills</h3>
              {renderFileSlot('Regular CGST', 'file_reg_cgst')}
              {renderFileSlot('Regular IGST', 'file_reg_igst')}
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-neutral-200 border-b border-white/[0.06] pb-2">RCM Bills</h3>
              {renderFileSlot('RCM CGST', 'file_rcm_cgst')}
              {renderFileSlot('RCM IGST', 'file_rcm_igst')}
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-neutral-200 border-b border-white/[0.06] pb-2">Import Purchases</h3>
              {renderFileSlot('Import CGST', 'file_import_cgst')}
              {renderFileSlot('Import IGST', 'file_import_igst')}
            </div>
          </div>

          <div className="flex-shrink-0 flex items-center justify-center lg:border-l border-white/[0.06] lg:pl-8 pt-6 lg:pt-0">
            <div className="flex flex-col items-center gap-3">
              <Button icon={Zap} loading={status === 'processing'} disabled={!Object.values(files).some(f => f !== null)} onClick={handleRunAutomation}>
                {status === 'processing' ? 'Processing' : 'Process Purchase Data'}
              </Button>
              {status === 'error' && <p className="text-red-400 text-xs text-center max-w-[180px]">{message}</p>}
            </div>
          </div>
        </div>
      </Card>

      {status === 'success' && blobUrl && (
        <div className="grid grid-cols-1 gap-6 animate-in slide-in-from-bottom-4 duration-700">
          <Card className="w-full max-w-sm mx-auto flex flex-col items-center justify-center text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-emerald-500" />
            <CheckCircle className="w-12 h-12 text-emerald-400 mb-4" />
            <h3 className="text-lg font-semibold text-neutral-50 mb-2">Conversion Complete</h3>
            <p className="text-sm text-neutral-500 mb-6">Your master purchase file has been downloaded.</p>
            <a
              href={blobUrl}
              download="Mario_Combined_Purchase.xlsx"
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-amber-500 hover:bg-amber-400 text-neutral-950 text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-amber-500/10"
            >
              <Download className="w-4 h-4" /> Download Again
            </a>
          </Card>
        </div>
      )}
    </div>
  );
}
