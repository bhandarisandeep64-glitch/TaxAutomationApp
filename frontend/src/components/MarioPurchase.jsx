import React, { useState } from 'react';
import { 
  FileText, 
  CheckCircle, 
  Download, 
  Flower, 
  X,
  Plus,
  ShoppingCart
} from 'lucide-react';
import { THEME } from '../constants/theme';

export default function MarioPurchase() {
  // 1. Specific states for our 6 Purchase files
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
      setFiles((prev) => ({
        ...prev,
        [name]: selectedFiles[0]
      }));
      setStatus('idle');
      setMessage('');
      setBlobUrl(null);
    }
  };

  const handleRemoveFile = (name) => {
    setFiles((prev) => ({
      ...prev,
      [name]: null
    }));
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
      if (files[key]) {
        formData.append(key, files[key]);
      }
    }

    try {
      // Pointing to your live Render backend for Purchases
      const response = await fetch('https://taxautomationapp.onrender.com/api/mario/purchase', {
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
      <div className="relative p-4 rounded-xl border border-dashed border-slate-700 hover:border-amber-500 bg-slate-900/50 transition-all flex flex-col justify-between h-full">
        <label className="text-xs font-bold text-slate-400 mb-3 block uppercase tracking-wider">{label}</label>
        
        {file ? (
          <div className="flex items-center justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-700 animate-in zoom-in-95">
            <div className="flex items-center gap-2 overflow-hidden">
              <FileText className="w-4 h-4 text-rose-500 flex-shrink-0" />
              <span className="text-xs text-slate-300 truncate">{file.name}</span>
            </div>
            <button onClick={() => handleRemoveFile(name)} className="text-slate-500 hover:text-red-400 ml-2 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="relative mt-auto">
            <input type="file" id={name} name={name} className="hidden" accept=".xlsx, .xls" onChange={handleFileChange} />
            <label 
              htmlFor={name} 
              className="cursor-pointer flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-slate-950 border border-slate-800 hover:bg-slate-800 hover:border-slate-600 text-slate-400 hover:text-white transition-all text-xs font-medium"
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
      
      {/* HEADER */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
        <ShoppingCart className={`w-6 h-6 ${THEME.accent}`} />
        <h2 className="text-xl font-bold text-white tracking-tight">Mario Purchase Converter <span className="text-slate-600">|</span> Odoo</h2>
      </div>

      {/* CONTROL PANEL */}
      <div className={`p-6 rounded-2xl border ${THEME.border} bg-slate-900/50 shadow-xl`}>
        <div className="flex flex-col lg:flex-row gap-8 items-stretch">
            
            {/* LEFT: 6 File Inputs arranged in 3 columns */}
            <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Regular Column */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-white border-b border-slate-800 pb-2">Regular Bills</h3>
                  {renderFileSlot('Regular CGST', 'file_reg_cgst')}
                  {renderFileSlot('Regular IGST', 'file_reg_igst')}
                </div>

                {/* RCM Column */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-white border-b border-slate-800 pb-2">RCM Bills</h3>
                  {renderFileSlot('RCM CGST', 'file_rcm_cgst')}
                  {renderFileSlot('RCM IGST', 'file_rcm_igst')}
                </div>

                {/* Import Column */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-white border-b border-slate-800 pb-2">Import Purchases</h3>
                  {renderFileSlot('Import CGST', 'file_import_cgst')}
                  {renderFileSlot('Import IGST', 'file_import_igst')}
                </div>

            </div>

            {/* RIGHT: Black Rose Button */}
            <div className="relative flex-shrink-0 flex items-center justify-center lg:border-l border-slate-800 lg:pl-8 pt-6 lg:pt-0">
                 <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-rose-900/20 blur-xl rounded-full pointer-events-none"></div>

                <div className="flex flex-col items-center gap-4">
                  <button 
                      onClick={handleRunAutomation} 
                      disabled={status === 'processing' || !Object.values(files).some(f => f !== null)}
                      className={`
                          group relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300
                          ${status === 'processing' 
                              ? 'bg-slate-900 border border-slate-800 cursor-not-allowed' 
                              : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_20px_rgba(225,29,72,0.4)] hover:scale-105 active:scale-95'
                          }
                          disabled:opacity-50 disabled:hover:scale-100 disabled:hover:shadow-none
                      `}
                      title="Process Purchase Data"
                  >
                      {status === 'processing' ? (
                          <span className="w-10 h-10 border-2 border-slate-600 border-t-transparent rounded-full animate-spin"></span>
                      ) : (
                          <Flower strokeWidth={1.5} className="w-10 h-10 text-rose-700 transition-all duration-500 group-hover:text-rose-500 group-hover:rotate-45 group-hover:scale-110" />
                      )}
                  </button>
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Process</span>
                </div>
                
                {status === 'error' && (
                     <div className="absolute top-full left-1/2 -translate-x-1/2 mt-4 whitespace-nowrap text-red-400 text-xs font-bold bg-red-950/90 px-3 py-1.5 rounded border border-red-900 shadow-xl">
                        {message}
                     </div>
                )}
            </div>
        </div>
      </div>

      {/* RESULTS SECTION */}
      {status === 'success' && blobUrl && (
        <div className="grid grid-cols-1 gap-6 animate-in slide-in-from-bottom-4 duration-700">
          <div className={`w-full max-w-sm mx-auto ${THEME.card} border ${THEME.border} p-6 rounded-xl flex flex-col items-center justify-center text-center relative overflow-hidden`}>
             <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-teal-400"></div>
             <CheckCircle className="w-12 h-12 text-emerald-400 mb-4" />
             <h3 className="text-lg font-bold text-white mb-2">Conversion Complete</h3>
             <p className="text-sm text-slate-400 mb-6">Your master purchase file has been downloaded.</p>
             <a 
                href={blobUrl} 
                download="Mario_Combined_Purchase.xlsx"
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold rounded-lg transition-all shadow-lg shadow-emerald-900/20"
             >
                <Download className="w-4 h-4" /> Download Again
             </a>
          </div>
        </div>
      )}
    </div>
  );
}