import React, { useState, useRef, useEffect } from 'react';
import { 
  Upload, 
  FileText, 
  CheckCircle, 
  Download, 
  Database, 
  X,
  Play,
  Layers,
  AlertCircle,
  Terminal as TerminalIcon,
  Flower
} from 'lucide-react';
import { THEME } from '../../constants/theme';

export default function RecoGSTR2B() {
  // State for files
  const [portalFile, setPortalFile] = useState(null);
  const [odooFiles, setOdooFiles] = useState({
    odoo_reg_cgst: null,
    odoo_reg_igst: null,
    odoo_rcm_cgst: null,
    odoo_rcm_igst: null
  });

  const [status, setStatus] = useState('idle'); // idle, processing, success, error
  const [logs, setLogs] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  
  const terminalRef = useRef(null);

  // --- HANDLERS ---
  const handlePortalChange = (e) => {
    if (e.target.files[0]) setPortalFile(e.target.files[0]);
  };

  const handleOdooChange = (key, e) => {
    if (e.target.files[0]) {
      setOdooFiles(prev => ({ ...prev, [key]: e.target.files[0] }));
    }
  };

  const removeFile = (type, key = null) => {
    if (type === 'portal') setPortalFile(null);
    else setOdooFiles(prev => ({ ...prev, [key]: null }));
    setStatus('idle');
  };

  // --- TERMINAL SIMULATION ---
  useEffect(() => {
    if (status === 'processing') {
      const steps = [
        "Initializing Reco Engine...",
        "Reading GSTR-2B Portal Data...",
        "Scanning Odoo Purchase Registers...",
        "Merging Regular & RCM Data...",
        "Performing Fuzzy Matching Logic...",
        "Generating Reconciliation Matrix..."
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

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  // --- API SUBMIT ---
  const handleRunReco = async () => {
    if (!portalFile) {
      setErrorMessage("Please upload the Portal GSTR-2B file.");
      return;
    }
    
    // Check if at least one Odoo file is uploaded
    const hasOdooFile = Object.values(odooFiles).some(f => f !== null);
    if (!hasOdooFile) {
      setErrorMessage("Please upload at least one Odoo Register file.");
      return;
    }

    setStatus('processing');
    setErrorMessage('');
    
    const formData = new FormData();
    formData.append('file_portal', portalFile);
    // Append Odoo files only if they exist
    Object.keys(odooFiles).forEach(key => {
      if (odooFiles[key]) formData.append(key, odooFiles[key]);
    });

    try {
      const response = await fetch('http://127.0.0.1:5000/api/indirect-tax/reco-gstr2b', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Reconciliation Failed');
      }

      // Visual delay for effect
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

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* HEADER */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
        <div className="p-2 bg-purple-900/10 rounded-lg border border-purple-500/20">
             <Database className={`w-6 h-6 text-purple-500`} />
        </div>
        <h2 className="text-xl font-bold text-white tracking-tight">GSTR-2B Reconciliation <span className="text-slate-600">|</span> Odoo vs Portal</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: INPUTS */}
        <div className="lg:col-span-2 space-y-6">
            
            {/* 1. PORTAL UPLOAD */}
            <div className={`p-5 rounded-xl border ${THEME.border} bg-slate-900/50`}>
                <h3 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2">
                    <span className="w-6 h-6 rounded bg-amber-500/20 text-amber-500 flex items-center justify-center text-xs">1</span>
                    Portal Data (GSTR-2B)
                </h3>
                
                {!portalFile ? (
                    <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-slate-700 rounded-lg cursor-pointer hover:bg-slate-800/50 hover:border-amber-500/50 transition-all group">
                        <div className="flex items-center gap-3 text-slate-400 group-hover:text-slate-200">
                            <Upload className="w-5 h-5" />
                            <span className="text-sm font-medium">Upload GSTR-2B Excel</span>
                        </div>
                        <input type="file" className="hidden" accept=".xlsx, .xls" onChange={handlePortalChange} />
                    </label>
                ) : (
                    <div className="flex items-center justify-between p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                        <div className="flex items-center gap-3">
                            <FileText className="w-5 h-5 text-amber-500" />
                            <span className="text-sm font-medium text-slate-200 truncate max-w-[250px]">{portalFile.name}</span>
                        </div>
                        <button onClick={() => removeFile('portal')} className="text-slate-500 hover:text-red-400"><X className="w-4 h-4"/></button>
                    </div>
                )}
            </div>

            {/* 2. ODOO UPLOADS */}
            <div className={`p-5 rounded-xl border ${THEME.border} bg-slate-900/50`}>
                <h3 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2">
                    <span className="w-6 h-6 rounded bg-purple-500/20 text-purple-500 flex items-center justify-center text-xs">2</span>
                    Odoo Registers (Upload Required Files)
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Mapping for the 4 files */}
                    {[
                        { id: 'odoo_reg_cgst', label: 'Regular CGST' },
                        { id: 'odoo_reg_igst', label: 'Regular IGST' },
                        { id: 'odoo_rcm_cgst', label: 'RCM CGST' },
                        { id: 'odoo_rcm_igst', label: 'RCM IGST' }
                    ].map((field) => (
                        <div key={field.id} className="space-y-2">
                            <p className="text-xs font-medium text-slate-500 uppercase">{field.label}</p>
                            {!odooFiles[field.id] ? (
                                <label className="flex items-center justify-center w-full h-12 border border-dashed border-slate-700 rounded-lg cursor-pointer hover:bg-slate-800 hover:border-purple-500/50 transition-all">
                                    <span className="text-xs text-slate-400 flex items-center gap-2">
                                        <Upload className="w-3 h-3" /> Select File
                                    </span>
                                    <input type="file" className="hidden" accept=".xlsx, .xls, .csv" onChange={(e) => handleOdooChange(field.id, e)} />
                                </label>
                            ) : (
                                <div className="flex items-center justify-between p-2 bg-slate-800 border border-slate-700 rounded-lg">
                                    <div className="flex items-center gap-2 overflow-hidden">
                                        <Layers className="w-3 h-3 text-purple-400 flex-shrink-0" />
                                        <span className="text-xs text-slate-300 truncate">{odooFiles[field.id].name}</span>
                                    </div>
                                    <button onClick={() => removeFile('odoo', field.id)} className="text-slate-500 hover:text-red-400"><X className="w-3 h-3"/></button>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

        </div>

        {/* RIGHT COLUMN: ACTIONS & LOGS */}
        <div className="flex flex-col gap-4">
            
            {/* ERROR BANNER */}
            {errorMessage && (
                <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg flex items-start gap-3 text-red-400 text-sm">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <span>{errorMessage}</span>
                </div>
            )}

            {/* BLACK ROSE BUTTON REPLACEMENT */}
            <div className="relative flex-shrink-0 self-center py-4">
                 {/* Subtle Glow behind button */}
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
            
            {/* Label for the button */}
            <div className="text-center text-xs font-medium text-slate-500 uppercase tracking-widest mb-2">
                {status === 'processing' ? 'Reconciling...' : 'Run Reco'}
            </div>

            {/* TERMINAL */}
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
                        <div key={i} className="text-purple-400/90 animate-in slide-in-from-left-2 fade-in duration-300">
                            <span className="text-slate-600 mr-2">{">"}</span>
                            {log}
                        </div>
                    ))}
                </div>
            </div>

            {/* SUCCESS DOWNLOAD */}
            {status === 'success' && downloadUrl && (
                <div className="animate-in slide-in-from-bottom-4 duration-500 p-4 bg-green-900/20 border border-green-500/30 rounded-xl">
                    <h4 className="text-green-400 font-bold text-sm mb-1 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4" /> Reconciliation Success
                    </h4>
                    <p className="text-slate-400 text-xs mb-3">Report generated successfully.</p>
                    <a 
                        href={downloadUrl} 
                        download={`GSTR2B_Reco_${new Date().toISOString().slice(0,10)}.xlsx`}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-xs font-bold rounded-lg transition-colors"
                    >
                        <Download className="w-3 h-3" /> Download Report
                    </a>
                </div>
            )}

        </div>
      </div>
    </div>
  );
}6