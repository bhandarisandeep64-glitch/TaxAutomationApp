import React, { useState, useEffect, useRef } from 'react';
import { 
  Upload, 
  FileText, 
  CheckCircle, 
  Download, 
  Landmark, 
  X,
  Play,
  FileSpreadsheet,
  Terminal as TerminalIcon,
  Flower
} from 'lucide-react';
import { THEME } from '../../constants/theme';

export default function FixedAssetRegister() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, processing, success, error
  const [logs, setLogs] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [finalFileName, setFinalFileName] = useState('');

  const terminalRef = useRef(null);

  // --- HANDLERS ---
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus('idle');
      setLogs([]);
      setDownloadUrl(null);
    }
  };

  const removeFile = () => {
    setFile(null);
    setStatus('idle');
    setLogs([]);
  };

  const downloadTemplate = () => {
    const headers = ["Asset Name", "Block Rate", "Opening WDV", "Addition Date", "Addition Amount", "Sale Amount"];
    const row1 = ["Office Laptop", "40", "50000", "01-12-2023", "150000", "0"];
    let csvContent = "data:text/csv;charset=utf-8," + headers.join(",") + "\n" + row1.join(",");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "Asset_Template.csv");
    document.body.appendChild(link);
    link.click();
  };

  // --- ENGINE LOGIC ---
  useEffect(() => {
    if (status === 'processing') {
      const steps = [
        "Initializing Python Pandas Engine...",
        "Reading Asset Data Structure...",
        "Applying Income Tax 180-Day Rule...",
        "Calculating Depreciation Blocks...",
        "Generating Closing WDV Report...",
        "Finalizing Artifacts..."
      ];
      
      let delay = 0;
      setLogs([]); 

      steps.forEach((step, index) => {
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

  const handleRunEngine = async () => {
    if (!file) return;

    setStatus('processing');
    const formData = new FormData();
    formData.append('file_assets', file);

    try {
      const response = await fetch('http://127.0.0.1:5000/api/fixed-assets/calculate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Calculation Failed');

      // Wait for logs animation to finish visually
      await new Promise(r => setTimeout(r, 5000));

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      setDownloadUrl(url);
      setFinalFileName(`FAR_${new Date().toISOString().slice(0,10)}.xlsx`);
      setStatus('success');
      setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] SUCCESS: Register Generated.`]);

    } catch (error) {
      setStatus('error');
      setLogs(prev => [...prev, `[ERROR] ${error.message}`]);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* HEADER */}
      <div className="flex items-center gap-3 border-b border-rose-900/20 pb-4">
        <div className="p-2 bg-rose-900/10 rounded-lg border border-rose-900/20">
            <Landmark className={`w-6 h-6 text-rose-500`} />
        </div>
        <h2 className="text-xl font-bold text-zinc-100 tracking-tight">Depreciation Calculator <span className="text-zinc-600">|</span> Income Tax</h2>
      </div>

      {/* MAIN CONTROL PANEL */}
      <div className="p-6 rounded-2xl border border-rose-900/20 bg-black/40 backdrop-blur-sm shadow-xl">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* LEFT: INPUTS */}
            <div className="lg:col-span-2 space-y-6">
                
                {/* Step 1: Template */}
                <div className="flex items-center justify-between p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/50">
                    <div className="flex items-center gap-3">
                        <FileSpreadsheet className="w-5 h-5 text-emerald-500" />
                        <div>
                            <h3 className="text-sm font-semibold text-zinc-200">Standard Format Required</h3>
                            <p className="text-xs text-zinc-500">Download the template to avoid column errors.</p>
                        </div>
                    </div>
                    {/* Updated to match Black Rose Theme colors, but kept rectangular for utility */}
                    <button 
                        onClick={downloadTemplate}
                        className="px-4 py-2 text-xs font-bold text-rose-500 bg-black border border-rose-900/50 rounded-lg hover:bg-zinc-900 hover:shadow-[0_0_10px_rgba(225,29,72,0.2)] transition-all"
                    >
                        Download Template
                    </button>
                </div>

                {/* Step 2: Upload */}
                <div>
                    {!file ? (
                        <div className="relative group">
                            <input type="file" id="far-upload" className="hidden" accept=".xlsx, .csv" onChange={handleFileChange} />
                            <label 
                                htmlFor="far-upload" 
                                className="cursor-pointer flex flex-col items-center justify-center gap-3 w-full h-32 rounded-xl border-2 border-dashed border-zinc-700 hover:border-rose-500/50 hover:bg-rose-900/5 transition-all group-hover:scale-[1.01]"
                            >
                                <div className="p-3 rounded-full bg-zinc-800 group-hover:bg-rose-900/20 transition-colors">
                                    <Upload className="w-5 h-5 text-zinc-400 group-hover:text-rose-500" />
                                </div>
                                <span className="text-sm font-medium text-zinc-400 group-hover:text-zinc-200">
                                    Upload Asset Excel File
                                </span>
                            </label>
                        </div>
                    ) : (
                        <div className="flex items-center justify-between p-4 rounded-xl border border-rose-500/20 bg-rose-500/5">
                            <div className="flex items-center gap-3">
                                <div className="p-2 rounded-lg bg-rose-500/10">
                                    <FileText className="w-5 h-5 text-rose-500" />
                                </div>
                                <div>
                                    <p className="text-sm font-bold text-white">{file.name}</p>
                                    <p className="text-xs text-rose-400/70">Ready for calculation</p>
                                </div>
                            </div>
                            <button onClick={removeFile} className="p-2 hover:bg-zinc-800 rounded-full text-zinc-400 hover:text-red-400 transition-colors">
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    )}
                </div>

            </div>

            {/* RIGHT: ACTION & TERMINAL */}
            <div className="flex flex-col gap-4">
                
                {/* BLACK ROSE BUTTON REPLACEMENT */}
                <div className="relative flex-shrink-0 self-center py-2">
                     {/* Subtle Glow behind button */}
                     <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-rose-900/20 blur-xl rounded-full pointer-events-none"></div>

                    <button 
                        onClick={handleRunEngine} 
                        disabled={!file || status === 'processing'}
                        className={`
                            group relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300
                            ${!file || status === 'processing' 
                                ? 'bg-slate-900 border border-slate-800 cursor-not-allowed' 
                                : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_20px_rgba(225,29,72,0.4)] hover:scale-105 active:scale-95'
                            }
                        `}
                        title="Run Depreciation Engine"
                    >
                        {status === 'processing' ? (
                            <span className="w-8 h-8 border-2 border-slate-600 border-t-transparent rounded-full animate-spin"></span>
                        ) : (
                            <Flower strokeWidth={1.5} className={`w-8 h-8 text-rose-700 transition-all duration-500 group-hover:text-rose-500 group-hover:rotate-45 group-hover:scale-110`} />
                        )}
                    </button>
                </div>
                
                {/* Label for the button since text is removed */}
                <div className="text-center text-xs font-medium text-zinc-500 uppercase tracking-widest">
                    {status === 'processing' ? 'Processing...' : 'Run Engine'}
                </div>

                {/* Terminal Window */}
                <div className="flex-1 bg-[#0a0a0a] rounded-xl border border-zinc-800 overflow-hidden flex flex-col min-h-[200px]">
                    <div className="px-4 py-2 border-b border-zinc-800 bg-zinc-900/50 flex items-center gap-2">
                        <TerminalIcon className="w-3 h-3 text-zinc-500" />
                        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">System Logs</span>
                    </div>
                    <div 
                        ref={terminalRef}
                        className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-2 scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent"
                    >
                        {logs.length === 0 && status === 'idle' && (
                            <span className="text-zinc-700 italic">// Waiting for input...</span>
                        )}
                        {logs.map((log, i) => (
                            <div key={i} className="text-rose-400/90 animate-in slide-in-from-left-2 fade-in duration-300">
                                <span className="text-zinc-600 mr-2">{">"}</span>
                                {log}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
      </div>

      {/* SUCCESS DOWNLOAD CARD */}
      {status === 'success' && downloadUrl && (
        <div className="animate-in slide-in-from-bottom-4 duration-700 bg-gradient-to-r from-emerald-900/20 to-green-900/20 border border-emerald-500/30 rounded-2xl p-6 flex items-center justify-between">
            <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-500/20 rounded-full">
                    <CheckCircle className="w-6 h-6 text-emerald-400" />
                </div>
                <div>
                    <h3 className="text-lg font-bold text-white">Calculation Complete</h3>
                    <p className="text-sm text-zinc-400">Your Fixed Asset Register is ready.</p>
                </div>
            </div>
            <a 
                href={downloadUrl} 
                download={finalFileName}
                className="flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold rounded-xl transition-all shadow-lg shadow-emerald-900/20 hover:-translate-y-0.5"
            >
                <Download className="w-4 h-4" />
                Download Report
            </a>
        </div>
      )}

    </div>
  );
}