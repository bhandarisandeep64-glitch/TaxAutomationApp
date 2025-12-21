import React, { useState, useRef, useEffect } from 'react';
import { 
  Upload, FileText, CheckCircle, Download, Database, X, AlertCircle, Terminal as TerminalIcon, Flower, Calendar, DollarSign, Wallet
} from 'lucide-react';

// Define theme locally to avoid import errors
const THEME = {
  accent: 'text-blue-500', 
  border: 'border-slate-800',
  card: 'bg-slate-950'
};

export default function RecoGSTR2BZoho() {
  const [portalFile, setPortalFile] = useState(null);
  const [zohoFile, setZohoFile] = useState(null);
  const [month, setMonth] = useState('');
  
  // New State for Manual Inputs
  const [sales, setSales] = useState({ taxable: '', igst: '', cgst: '', sgst: '' });
  const [opening, setOpening] = useState({ igst: '', cgst: '', sgst: '' });

  const [status, setStatus] = useState('idle');
  const [logs, setLogs] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const terminalRef = useRef(null);

  const handleFileChange = (type, e) => {
    if (e.target.files[0]) {
        if (type === 'portal') setPortalFile(e.target.files[0]);
        else setZohoFile(e.target.files[0]);
        setStatus('idle');
    }
  };

  const removeFile = (type) => {
    if (type === 'portal') setPortalFile(null);
    else setZohoFile(null);
    setStatus('idle');
  };

  const handleInputChange = (category, field, value) => {
      if (category === 'sales') setSales(prev => ({ ...prev, [field]: value }));
      if (category === 'opening') setOpening(prev => ({ ...prev, [field]: value }));
  };

  // --- ENGINE LOGIC ---
  useEffect(() => {
    if (status === 'processing') {
      const steps = [
        "Initializing Max Advance Engine...",
        "Reading GSTR-2B Portal Data...",
        "Scanning Zoho Books Export...",
        "Calculating Section 49 Offsets...",
        "Matching Invoices (Fuzzy Logic)...",
        "Generating Master Dashboard..."
      ];
      let delay = 0;
      setLogs([]); 
      steps.forEach((step) => {
        setTimeout(() => {
          setLogs(prev => [...prev, `[${new Date().toLocaleTimeString('en-US',{hour12:false})}] ${step}`]);
        }, delay);
        delay += 800;
      });
    }
  }, [status]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const handleRunReco = async () => {
    if (!portalFile || !zohoFile) {
      setErrorMessage("Please upload both files.");
      return;
    }

    setStatus('processing');
    setErrorMessage('');
    
    const formData = new FormData();
    // Files
    formData.append('file_portal', portalFile);
    formData.append('file_zoho', zohoFile);
    
    // New Inputs
    formData.append('month', month);
    
    formData.append('sales_taxable', sales.taxable);
    formData.append('sales_igst', sales.igst);
    formData.append('sales_cgst', sales.cgst);
    formData.append('sales_sgst', sales.sgst);

    formData.append('op_igst', opening.igst);
    formData.append('op_cgst', opening.cgst);
    formData.append('op_sgst', opening.sgst);

    try {
      const response = await fetch('https://taxautomationapp.onrender.com/api/indirect-tax/reco-gstr2b-zoho', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Reconciliation Failed');
      }

      await new Promise(r => setTimeout(r, 5000));

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      setDownloadUrl(url);
      setStatus('success');
      setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] SUCCESS: Reconciliation Complete.`]);

    } catch (error) {
      setStatus('error');
      setErrorMessage(error.message);
      setLogs(prev => [...prev, `[CRITICAL ERROR] ${error.message}`]);
    }
  };

  // Helper for Input Fields
  const renderCurrencyInput = (label, value, onChange) => (
      <div className="group">
          <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1 group-hover:text-blue-400 transition-colors">
              {label}
          </label>
          <div className="relative">
              <span className="absolute left-2 top-2 text-slate-600 text-xs">₹</span>
              <input 
                  type="number" 
                  value={value}
                  onChange={(e) => onChange(e.target.value)}
                  placeholder="0.00"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg py-1.5 pl-6 pr-2 text-sm text-slate-300 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              />
          </div>
      </div>
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500 pb-10">
      
      {/* HEADER */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
        <div className="p-2 bg-blue-900/10 rounded-lg border border-blue-500/20">
             <Database className={`w-6 h-6 ${THEME.accent}`} />
        </div>
        <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Max Advance GST Reco</h2>
            <p className="text-xs text-slate-500">Automated GSTR-3B & Payment Offset Engine</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: INPUTS */}
        <div className="lg:col-span-2 space-y-5">
            
            {/* 1. DATA SOURCES */}
            <div className={`p-5 rounded-xl border ${THEME.border} bg-slate-900/50`}>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                        <span className="w-6 h-6 rounded bg-amber-500/20 text-amber-500 flex items-center justify-center text-xs">1</span>
                        Data Sources
                    </h3>
                    <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-slate-500" />
                        <input 
                            type="month" 
                            value={month}
                            onChange={(e) => setMonth(e.target.value)}
                            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded px-2 py-1 outline-none focus:border-blue-500"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Portal Upload */}
                    {!portalFile ? (
                        <label className="flex flex-col items-center justify-center h-24 border-2 border-dashed border-slate-700 rounded-lg cursor-pointer hover:bg-slate-800/50 hover:border-amber-500/50 transition-all group">
                            <Upload className="w-5 h-5 text-slate-500 group-hover:text-slate-300 mb-2" />
                            <span className="text-xs font-medium text-slate-400">Upload Portal (GSTR-2B)</span>
                            <input type="file" className="hidden" accept=".xlsx, .xls" onChange={(e) => handleFileChange('portal', e)} />
                        </label>
                    ) : (
                        <div className="flex items-center justify-between p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                            <div className="flex items-center gap-2 truncate">
                                <FileText className="w-4 h-4 text-amber-500 flex-shrink-0" />
                                <span className="text-xs text-slate-300 truncate">{portalFile.name}</span>
                            </div>
                            <button onClick={() => removeFile('portal')}><X className="w-4 h-4 text-slate-500 hover:text-red-400"/></button>
                        </div>
                    )}

                    {/* Zoho Upload */}
                    {!zohoFile ? (
                        <label className="flex flex-col items-center justify-center h-24 border-2 border-dashed border-slate-700 rounded-lg cursor-pointer hover:bg-slate-800/50 hover:border-blue-500/50 transition-all group">
                            <Upload className="w-5 h-5 text-slate-500 group-hover:text-slate-300 mb-2" />
                            <span className="text-xs font-medium text-slate-400">Upload Zoho Export</span>
                            <input type="file" className="hidden" accept=".xlsx, .xls" onChange={(e) => handleFileChange('zoho', e)} />
                        </label>
                    ) : (
                        <div className="flex items-center justify-between p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                            <div className="flex items-center gap-2 truncate">
                                <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
                                <span className="text-xs text-slate-300 truncate">{zohoFile.name}</span>
                            </div>
                            <button onClick={() => removeFile('zoho')}><X className="w-4 h-4 text-slate-500 hover:text-red-400"/></button>
                        </div>
                    )}
                </div>
            </div>

            {/* 2. SALES INPUTS */}
            <div className={`p-5 rounded-xl border ${THEME.border} bg-slate-900/50`}>
                <h3 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2">
                    <span className="w-6 h-6 rounded bg-blue-500/20 text-blue-500 flex items-center justify-center text-xs">2</span>
                    Outward Supplies (Sales)
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {renderCurrencyInput('Taxable Value', sales.taxable, (v) => handleInputChange('sales', 'taxable', v))}
                    {renderCurrencyInput('IGST', sales.igst, (v) => handleInputChange('sales', 'igst', v))}
                    {renderCurrencyInput('CGST', sales.cgst, (v) => handleInputChange('sales', 'cgst', v))}
                    {renderCurrencyInput('SGST', sales.sgst, (v) => handleInputChange('sales', 'sgst', v))}
                </div>
            </div>

            {/* 3. OPENING BALANCE */}
            <div className={`p-5 rounded-xl border ${THEME.border} bg-slate-900/50`}>
                <h3 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2">
                    <span className="w-6 h-6 rounded bg-purple-500/20 text-purple-500 flex items-center justify-center text-xs">3</span>
                    Opening ITC Balance
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="hidden md:flex items-center text-xs text-slate-500 italic">
                        From Electronic Credit Ledger
                    </div>
                    {renderCurrencyInput('Opening IGST', opening.igst, (v) => handleInputChange('opening', 'igst', v))}
                    {renderCurrencyInput('Opening CGST', opening.cgst, (v) => handleInputChange('opening', 'cgst', v))}
                    {renderCurrencyInput('Opening SGST', opening.sgst, (v) => handleInputChange('opening', 'sgst', v))}
                </div>
            </div>

        </div>

        {/* RIGHT COLUMN: ACTIONS */}
        <div className="flex flex-col gap-4">
            {errorMessage && (
                <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg flex items-start gap-3 text-red-400 text-sm">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <span>{errorMessage}</span>
                </div>
            )}

            {/* BLACK ROSE BUTTON */}
            <div className="relative flex-shrink-0 self-center py-4">
                 <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-rose-900/20 blur-xl rounded-full pointer-events-none"></div>

                <button 
                    onClick={handleRunReco} 
                    disabled={status === 'processing'}
                    className={`
                        group relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300
                        ${status === 'processing' 
                            ? 'bg-slate-900 border border-slate-800 cursor-not-allowed' 
                            : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_20px_rgba(225,29,72,0.4)] hover:scale-105 active:scale-95'
                        }
                    `}
                    title="Run Reconciliation"
                >
                    {status === 'processing' ? (
                        <span className="w-8 h-8 border-2 border-slate-600 border-t-transparent rounded-full animate-spin"></span>
                    ) : (
                        <Flower strokeWidth={1.5} className={`w-8 h-8 text-rose-700 transition-all duration-500 group-hover:text-rose-500 group-hover:rotate-45 group-hover:scale-110`} />
                    )}
                </button>
            </div>
            
            <div className="text-center text-xs font-medium text-slate-500 uppercase tracking-widest mb-2">
                {status === 'processing' ? 'Processing...' : 'Generate Report'}
            </div>

            <div className="flex-1 bg-slate-950 rounded-xl border border-slate-800 overflow-hidden flex flex-col min-h-[250px]">
                <div className="px-4 py-2 border-b border-slate-800 bg-slate-900/50 flex items-center gap-2">
                    <TerminalIcon className="w-3 h-3 text-slate-500" />
                    <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Engine Logs</span>
                </div>
                <div 
                    ref={terminalRef}
                    className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-2 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent"
                >
                    {logs.length === 0 && status === 'idle' && (
                        <span className="text-slate-700 italic">// Ready to reconcile...</span>
                    )}
                    {logs.map((log, i) => (
                        <div key={i} className="text-blue-400/90 animate-in slide-in-from-left-2 fade-in duration-300">
                            <span className="text-slate-600 mr-2">{">"}</span>
                            {log}
                        </div>
                    ))}
                </div>
            </div>

            {status === 'success' && downloadUrl && (
                <div className="animate-in slide-in-from-bottom-4 duration-500 p-4 bg-green-900/20 border border-green-500/30 rounded-xl">
                    <h4 className="text-green-400 font-bold text-sm mb-1 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4" /> Reconciliation Success
                    </h4>
                    <a 
                        href={downloadUrl} 
                        download={`Max_Reco_${new Date().toISOString().slice(0,10)}.xlsx`}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 mt-2 bg-green-600 hover:bg-green-500 text-white text-xs font-bold rounded-lg transition-colors"
                    >
                        <Download className="w-3 h-3" /> Download Report
                    </a>
                </div>
            )}
        </div>
      </div>
    </div>
  );
}