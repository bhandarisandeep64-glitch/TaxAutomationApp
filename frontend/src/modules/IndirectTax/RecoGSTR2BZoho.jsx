import React, { useState, useRef, useEffect } from 'react';
import { 
  Upload, FileText, CheckCircle, Download, Database, X, 
  AlertCircle, Terminal as TerminalIcon, Flower, 
  TrendingUp, Wallet, Calendar, Shield, Cpu, Activity,
  Server, ArrowRight, Disc, MessageSquare, Sparkles, Brain, 
  Send as SendIcon, Loader, Bot
} from 'lucide-react';

export default function RecoGSTR2BZoho() {
  // --- PRESERVED STATE ---
  const [portalFile, setPortalFile] = useState(null);
  const [zohoFile, setZohoFile] = useState(null);
  const [status, setStatus] = useState('idle');
  const [logs, setLogs] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  
  const [inputs, setInputs] = useState({
    month: '',
    sales_taxable: '', sales_igst: '', sales_cgst: '', sales_sgst: '',
    op_igst: '', op_cgst: '', op_sgst: ''
  });

  const terminalRef = useRef(null);

  // --- GEMINI AI STATE ---
  const [showChat, setShowChat] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    { role: 'ai', text: 'Neural Link established. I am the Black Rose Tax Assistant. Query me regarding GST protocols or reconciliation logic.' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [aiSummary, setAiSummary] = useState(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const chatEndRef = useRef(null);

  // --- GEMINI API FUNCTION ---
  const callGeminiAPI = async (prompt, systemInstruction = '') => {
    const apiKey = ""; // Provided by environment at runtime
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`;
    
    const payload = {
      contents: [{ parts: [{ text: prompt }] }],
      systemInstruction: systemInstruction ? { parts: [{ text: systemInstruction }] } : undefined
    };

    let attempt = 0;
    const delays = [1000, 2000, 4000, 8000, 16000];

    while (attempt <= 5) {
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error(`API Error: ${response.status}`);

        const data = await response.json();
        return data.candidates?.[0]?.content?.parts?.[0]?.text || "No response generated.";
      } catch (err) {
        if (attempt === 5) throw err;
        await new Promise(r => setTimeout(r, delays[attempt]));
        attempt++;
      }
    }
  };

  // --- AI HANDLERS ---
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput;
    setChatMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setChatInput('');
    setIsChatLoading(true);

    try {
      const systemPrompt = "You are 'Black Rose AI', a sophisticated, slightly futuristic tax automation assistant. Your persona is professional, concise, and technically precise. You help users with Indian GST (GSTR-2B, ITC) and Zoho Books reconciliation queries. Keep answers under 80 words unless detailed explanation is requested.";
      const aiResponse = await callGeminiAPI(userMsg, systemPrompt);
      setChatMessages(prev => [...prev, { role: 'ai', text: aiResponse }]);
    } catch (error) {
      setChatMessages(prev => [...prev, { role: 'ai', text: "Connection interrupted. Neural Link unstable." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (logs.length === 0) return;
    setIsSummarizing(true);
    try {
      const prompt = `Analyze the following system logs from a GSTR-2B vs Zoho Books reconciliation process:
      ${logs.join('\n')}
      
      Provide a professional, executive summary of the reconciliation run. 
      - Highlight if it was successful.
      - Mention the steps taken (e.g., fuzzy logic, RCM purging).
      - Maintain a 'cyber-security/financial-tech' tone. 
      - Keep it brief (bullet points).`;
      
      const summary = await callGeminiAPI(prompt);
      setAiSummary(summary);
    } catch (error) {
      setAiSummary("Failed to generate analysis matrix.");
    } finally {
      setIsSummarizing(false);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, showChat]);


  // --- PRESERVED LOGIC ---
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

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setInputs(prev => ({ ...prev, [name]: value }));
  };

  // Engine Logic Effects
  useEffect(() => {
    if (status === 'processing') {
      const steps = [
        "Initializing Neural Core...",
        "Reading GSTR-2B Portal Stream...",
        "Scanning Zoho Books Ledger...",
        "Normalizing Data Structures...",
        "Applying Manual Overrides & Opening Balances...",
        "Purging Duplicate RCM Entries...",
        "Executing Fuzzy Logic Matching Algorithm...",
        "Compiling Reconciliation Matrix..."
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
      setErrorMessage("PROTOCOL HALTED: Source files missing.");
      return;
    }

    setStatus('processing');
    setErrorMessage('');
    setAiSummary(null); // Reset summary on new run
    
    const formData = new FormData();
    formData.append('file_portal', portalFile);
    formData.append('file_zoho', zohoFile);

    Object.keys(inputs).forEach(key => {
        formData.append(key, inputs[key]);
    });

    try {
      const response = await fetch('https://taxautomationapp.onrender.com/api/indirect-tax/reco-gstr2b-zoho', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Reconciliation Failed');
      }

      await new Promise(r => setTimeout(r, 6500)); // Sync with logs

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      setDownloadUrl(url);
      setStatus('success');
      setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] SUCCESS: Report Generated.`]);

    } catch (error) {
      setStatus('error');
      setErrorMessage(error.message);
      setLogs(prev => [...prev, `[CRITICAL FAILURE] ${error.message}`]);
    }
  };

  // --- COMPACT UI COMPONENTS ---

  // 1. Sleek Input Field
  const CyberInput = ({ label, name, value, onChange, prefix }) => (
    <div className="group relative flex items-center justify-between bg-black/20 border border-zinc-800 rounded-lg p-1 pr-3 focus-within:border-rose-500/50 focus-within:bg-black/40 transition-all hover:border-zinc-700">
        <div className="flex flex-col px-3 py-1">
             <label className="text-[9px] font-mono text-zinc-500 uppercase tracking-wider group-focus-within:text-rose-400 transition-colors">
                {label}
             </label>
        </div>
        <div className="flex items-center">
            {prefix && <span className="text-zinc-600 text-xs font-mono mr-1">{prefix}</span>}
            <input
                type="number"
                name={name}
                value={value}
                onChange={onChange}
                placeholder="0.00"
                className="w-20 bg-transparent text-right text-xs font-mono text-white placeholder-zinc-700 focus:outline-none"
            />
        </div>
    </div>
  );

  // 2. Compact File Row (Replaces the big box)
  const CompactFileRow = ({ label, file, onFileChange, onRemove, accentColor, icon: Icon }) => {
    // Dynamic color classes
    const colors = {
      rose: { bg: 'bg-rose-500/10', text: 'text-rose-500', border: 'hover:border-rose-500/30' },
      amber: { bg: 'bg-amber-500/10', text: 'text-amber-500', border: 'hover:border-amber-500/30' },
      blue: { bg: 'bg-blue-500/10', text: 'text-blue-500', border: 'hover:border-blue-500/30' },
    }[accentColor] || { bg: 'bg-zinc-500/10', text: 'text-zinc-500', border: 'hover:border-zinc-500/30' };

    return (
      <div className={`flex items-center justify-between p-2.5 bg-black/40 border border-zinc-800/60 rounded-lg transition-all ${colors.border} group`}>
         <div className="flex items-center gap-3">
             {/* Icon Box */}
             <div className={`w-8 h-8 rounded-md ${colors.bg} flex items-center justify-center border border-white/5`}>
                 <Icon className={`w-4 h-4 ${colors.text}`} />
             </div>
             {/* Text Info */}
             <div className="flex flex-col">
                 <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">{label}</span>
                 {file ? (
                    <span className="text-xs font-medium text-white truncate max-w-[140px] md:max-w-[200px] flex items-center gap-1.5">
                       {file.name} <CheckCircle className={`w-3 h-3 ${colors.text}`} />
                    </span>
                 ) : (
                    <span className="text-xs text-zinc-700 italic">Waiting for data stream...</span>
                 )}
             </div>
         </div>

         {/* Action Button */}
         {file ? (
            <button 
                onClick={onRemove}
                className="p-1.5 rounded-md hover:bg-red-900/20 text-zinc-600 hover:text-red-400 transition-colors"
                title="Remove File"
            >
                <X className="w-4 h-4" />
            </button>
         ) : (
            <label className="cursor-pointer relative overflow-hidden group/btn">
                <input type="file" className="hidden" accept=".xlsx, .xls" onChange={onFileChange} />
                <div className={`px-3 py-1.5 rounded bg-zinc-900 border border-zinc-700 flex items-center gap-2 transition-all hover:bg-zinc-800 hover:border-${accentColor}-500/50`}>
                    <Upload className="w-3 h-3 text-zinc-400 group-hover/btn:text-white" />
                    <span className="text-[10px] font-bold text-zinc-400 uppercase group-hover/btn:text-white">Load</span>
                </div>
            </label>
         )}
      </div>
    );
  }

  return (
    <div className="relative min-h-screen w-full bg-[#050001] flex justify-center p-4 md:p-8 overflow-x-hidden font-sans selection:bg-rose-900/50 selection:text-white">
      
      {/* --- BACKGROUND FX --- */}
      <div className="absolute inset-0 z-0 opacity-[0.05] pointer-events-none mix-blend-overlay"
           style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} 
      />
      <div className="absolute top-[-200px] left-1/4 w-[600px] h-[600px] bg-rose-900/10 blur-[150px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-200px] right-1/4 w-[500px] h-[500px] bg-blue-900/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="relative z-10 w-full max-w-7xl animate-in fade-in zoom-in-95 duration-700">
        
        {/* --- HEADER --- */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between border-b border-white/5 pb-6 mb-8 gap-4">
            <div className="flex items-center gap-4">
                <div className="p-3 bg-gradient-to-br from-zinc-900 to-black rounded-xl border border-rose-500/20 shadow-lg shadow-rose-900/10">
                    <Database className="w-6 h-6 text-rose-500" />
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-white tracking-tight">Reconciliation <span className="text-rose-600">Core</span></h2>
                    <div className="flex items-center gap-2 mt-1">
                         <span className="px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[10px] font-mono text-zinc-400">V.2.0.4</span>
                         <span className="text-zinc-600 text-xs">|</span>
                         <p className="text-xs text-zinc-500 font-medium uppercase tracking-wide">GSTR-2B vs. Zoho Books</p>
                    </div>
                </div>
            </div>
            
            <div className="flex items-center gap-3">
                 {/* NEURAL LINK BUTTON */}
                <button 
                  onClick={() => setShowChat(!showChat)}
                  className={`flex items-center gap-2 px-4 py-1.5 rounded-full border text-xs font-mono transition-all ${
                    showChat 
                    ? 'bg-rose-900/20 border-rose-500/50 text-rose-400 shadow-[0_0_15px_rgba(225,29,72,0.3)]' 
                    : 'bg-zinc-900/50 border-zinc-800 text-zinc-400 hover:border-rose-500/30 hover:text-rose-400'
                  }`}
                >
                   <Brain className="w-3.5 h-3.5" />
                   {showChat ? 'NEURAL LINK ACTIVE' : 'OPEN NEURAL LINK'}
                </button>

                {/* Status Pill */}
                <div className={`px-4 py-1.5 rounded-full border text-xs font-mono flex items-center gap-2 ${
                    status === 'processing' ? 'bg-amber-900/20 border-amber-500/30 text-amber-500' :
                    status === 'success' ? 'bg-green-900/20 border-green-500/30 text-green-400' :
                    status === 'error' ? 'bg-red-900/20 border-red-500/30 text-red-400' :
                    'bg-zinc-900/50 border-zinc-800 text-zinc-400'
                }`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${status === 'processing' ? 'bg-amber-500 animate-ping' : status === 'success' ? 'bg-green-500' : status === 'error' ? 'bg-red-500' : 'bg-zinc-500'}`} />
                    {status === 'idle' ? 'SYSTEM READY' : status.toUpperCase()}
                </div>
            </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 relative">
        
          {/* --- LEFT COLUMN: INPUTS (8/12) --- */}
          <div className="lg:col-span-8 space-y-6">
            
            {/* 1. DATA SOURCES (Refined & Compact) */}
            <div className="rounded-2xl bg-zinc-900/30 backdrop-blur-md border border-white/5 p-6 relative overflow-hidden">
                <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded flex items-center justify-center bg-rose-500/20 text-rose-500 text-xs font-bold font-mono">1</div>
                        <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-wider">Source Ingestion</h3>
                    </div>
                    {/* Compact Month Picker */}
                    <div className="flex items-center gap-3 px-3 py-1.5 rounded-lg bg-black/20 border border-zinc-800">
                        <Calendar className="w-3.5 h-3.5 text-zinc-500" />
                        <div className="h-4 w-px bg-zinc-800" />
                        <input 
                            type="month" 
                            name="month"
                            value={inputs.month}
                            onChange={handleInputChange}
                            className="bg-transparent text-xs font-mono text-zinc-300 focus:outline-none uppercase"
                        />
                    </div>
                </div>

                <div className="flex flex-col gap-3">
                    <CompactFileRow 
                        label="GST Portal Data (XLSX)"
                        file={portalFile} 
                        onFileChange={(e) => handleFileChange('portal', e)} 
                        onRemove={() => removeFile('portal')}
                        accentColor="amber"
                        icon={FileText}
                    />
                    <CompactFileRow 
                        label="Zoho Books Data (XLSX)"
                        file={zohoFile} 
                        onFileChange={(e) => handleFileChange('zoho', e)} 
                        onRemove={() => removeFile('zoho')}
                        accentColor="blue"
                        icon={Database}
                    />
                </div>
            </div>

            {/* 2. FINANCIAL INPUTS (Refined & Compact) */}
            <div className="rounded-2xl bg-zinc-900/30 backdrop-blur-md border border-white/5 p-6 relative overflow-hidden">
                <div className="flex items-center gap-2 mb-6">
                    <div className="w-5 h-5 rounded flex items-center justify-center bg-emerald-500/20 text-emerald-500 text-xs font-bold font-mono">2</div>
                    <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-wider">Manual Telemetry</h3>
                    <div className="h-px flex-1 bg-gradient-to-r from-zinc-800 to-transparent ml-4" />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
                    
                    {/* Sales Section */}
                    <div className="space-y-3">
                        <div className="flex items-center gap-2 mb-1">
                             <TrendingUp className="w-3 h-3 text-emerald-500" />
                             <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Outward Supplies</span>
                        </div>
                        <div className="space-y-2">
                            <CyberInput label="Taxable" name="sales_taxable" value={inputs.sales_taxable} onChange={handleInputChange} prefix="₹" />
                            <div className="grid grid-cols-3 gap-2">
                                <CyberInput label="IGST" name="sales_igst" value={inputs.sales_igst} onChange={handleInputChange} />
                                <CyberInput label="CGST" name="sales_cgst" value={inputs.sales_cgst} onChange={handleInputChange} />
                                <CyberInput label="SGST" name="sales_sgst" value={inputs.sales_sgst} onChange={handleInputChange} />
                            </div>
                        </div>
                    </div>

                    {/* Opening Balance Section */}
                    <div className="space-y-3">
                        <div className="flex items-center gap-2 mb-1">
                             <Wallet className="w-3 h-3 text-purple-500" />
                             <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Opening ITC</span>
                        </div>
                        <div className="space-y-2">
                             <CyberInput label="Op. IGST" name="op_igst" value={inputs.op_igst} onChange={handleInputChange} prefix="₹" />
                             <div className="grid grid-cols-2 gap-2">
                                <CyberInput label="Op. CGST" name="op_cgst" value={inputs.op_cgst} onChange={handleInputChange} prefix="₹" />
                                <CyberInput label="Op. SGST" name="op_sgst" value={inputs.op_sgst} onChange={handleInputChange} prefix="₹" />
                             </div>
                        </div>
                    </div>
                </div>
            </div>

          </div>

          {/* --- RIGHT COLUMN: EXECUTION (4/12) --- */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            
            {/* Error Display */}
            {errorMessage && (
                <div className="animate-in slide-in-from-right-4 fade-in duration-300 p-3 bg-red-950/30 border border-red-500/50 rounded-lg flex items-start gap-3 backdrop-blur-md">
                    <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                    <div>
                        <h4 className="text-red-400 font-bold text-[10px] uppercase tracking-wider">Protocol Halted</h4>
                        <p className="text-red-300/80 text-[10px] mt-0.5">{errorMessage}</p>
                    </div>
                </div>
            )}

            {/* BLACK ROSE BUTTON */}
            <div className="flex flex-col items-center justify-center py-4 relative">
                 {/* Decorative Rings */}
                 <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full border border-dashed border-zinc-800 transition-all duration-1000 ${status === 'processing' ? 'animate-spin-slow opacity-100' : 'opacity-20'}`} />
                 
                 {/* Glow Behind */}
                 <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-rose-900/40 blur-2xl rounded-full pointer-events-none" />

                <button 
                    onClick={handleRunReco} 
                    disabled={status === 'processing'}
                    className={`
                        group relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-500
                        ${status === 'processing' 
                            ? 'bg-black border border-zinc-800 cursor-not-allowed scale-95' 
                            : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_40px_rgba(225,29,72,0.4)] hover:scale-105 active:scale-95'
                        }
                    `}
                >
                    {status === 'processing' ? (
                        <>
                           <div className="absolute inset-0 rounded-full border-t-2 border-r-2 border-rose-600 animate-spin"></div>
                           <Cpu className="w-8 h-8 text-rose-800 animate-pulse" />
                        </>
                    ) : (
                        <>
                           <span className="absolute inset-0 rounded-full bg-gradient-to-br from-rose-900/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                           <Flower strokeWidth={1} className="w-10 h-10 text-rose-700 transition-all duration-700 group-hover:text-rose-500 group-hover:rotate-180 group-hover:scale-110" />
                        </>
                    )}
                </button>
                
                <div className="mt-4 text-center">
                     <p className="text-xs font-bold text-zinc-400 uppercase tracking-[0.2em] group-hover:text-white transition-colors">
                        {status === 'processing' ? 'Processing...' : 'Initiate'}
                     </p>
                </div>
            </div>

            {/* HOLOGRAPHIC TERMINAL */}
            <div className="flex-1 bg-black rounded-xl border border-zinc-800 overflow-hidden flex flex-col min-h-[300px] shadow-2xl relative">
                <div className="absolute inset-0 pointer-events-none z-10 opacity-[0.03] bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))]" style={{backgroundSize: "100% 2px, 3px 100%"}} />

                <div className="px-4 py-2 bg-zinc-900/80 border-b border-zinc-800 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <TerminalIcon className="w-3 h-3 text-rose-500" />
                        <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-widest">Sys.Log</span>
                    </div>
                    <div className="flex gap-1.5">
                        <div className="w-2 h-2 rounded-full bg-zinc-700" />
                        <div className="w-2 h-2 rounded-full bg-zinc-700" />
                    </div>
                </div>

                <div 
                    ref={terminalRef}
                    className="flex-1 p-4 overflow-y-auto font-mono text-[10px] md:text-xs space-y-1.5 scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-black"
                >
                    {logs.length === 0 && status === 'idle' && (
                        <div className="flex flex-col items-center justify-center h-full opacity-30 text-zinc-500 space-y-2">
                            <Activity className="w-8 h-8" />
                            <span>// Awaiting Input //</span>
                        </div>
                    )}
                    {logs.map((log, i) => {
                        const isError = log.includes("ERROR") || log.includes("FAILURE");
                        const isSuccess = log.includes("SUCCESS");
                        return (
                            <div key={i} className={`flex items-start gap-2 ${isError ? 'text-red-500' : isSuccess ? 'text-green-400' : 'text-blue-400/80'} animate-in slide-in-from-left-2 fade-in duration-300`}>
                                <span className="opacity-50 shrink-0">{">"}</span>
                                <span className="break-all leading-relaxed">{log}</span>
                            </div>
                        )
                    })}
                    {status === 'processing' && (
                        <div className="w-2 h-4 bg-rose-500/50 animate-pulse mt-1" />
                    )}
                </div>
            </div>

            {/* AI SUMMARY & DOWNLOAD */}
            {status === 'success' && downloadUrl && (
                <div className="space-y-4 animate-in slide-in-from-bottom-8 duration-700">
                    
                    {/* Gemini AI Analysis Button */}
                    {!aiSummary ? (
                       <button 
                         onClick={handleGenerateSummary}
                         disabled={isSummarizing}
                         className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-rose-500/30 bg-rose-900/10 hover:bg-rose-900/20 text-rose-300 text-xs font-bold transition-all group"
                       >
                         {isSummarizing ? (
                           <Loader className="w-4 h-4 animate-spin" />
                         ) : (
                           <Sparkles className="w-4 h-4 group-hover:text-rose-100" />
                         )}
                         {isSummarizing ? 'Running Neural Analysis...' : 'Generate AI Executive Summary'}
                       </button>
                    ) : (
                       <div className="p-4 bg-zinc-900/80 border border-zinc-700 rounded-xl relative overflow-hidden animate-in fade-in duration-500">
                          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-rose-500 via-purple-500 to-blue-500" />
                          <div className="flex items-center gap-2 mb-2">
                             <Bot className="w-4 h-4 text-rose-400" />
                             <h4 className="text-xs font-bold text-white uppercase tracking-wider">AI Executive Summary</h4>
                          </div>
                          <p className="text-[10px] md:text-xs text-zinc-300 font-mono leading-relaxed whitespace-pre-wrap">
                            {aiSummary}
                          </p>
                       </div>
                    )}

                    {/* Download Button */}
                    <a 
                        href={downloadUrl} 
                        download={`Zoho_Reco_${new Date().toISOString().slice(0,10)}.xlsx`}
                        className="group w-full flex items-center justify-between p-1 pl-4 pr-1 bg-gradient-to-r from-emerald-900/40 to-emerald-900/10 border border-emerald-500/30 hover:border-emerald-400/50 rounded-xl transition-all"
                    >
                        <div className="flex flex-col">
                            <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-wider">Report Ready</span>
                            <span className="text-xs text-emerald-200">Download Excel Analysis</span>
                        </div>
                        <div className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center group-hover:scale-105 transition-transform text-black">
                            <Download className="w-5 h-5" />
                        </div>
                    </a>
                </div>
            )}
            
          </div>

           {/* --- NEURAL CHAT OVERLAY (Right Side Slide-out) --- */}
           {showChat && (
              <div className="absolute top-0 right-0 w-full md:w-[350px] h-full z-50 animate-in slide-in-from-right duration-300 shadow-2xl">
                 <div className="w-full h-full bg-black/90 backdrop-blur-xl border-l border-white/10 flex flex-col relative">
                     {/* Chat Header */}
                     <div className="p-4 border-b border-white/5 flex items-center justify-between bg-zinc-900/50">
                        <div className="flex items-center gap-2">
                           <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                           <span className="text-xs font-bold text-white uppercase tracking-widest">Neural Tax Assistant</span>
                        </div>
                        <button onClick={() => setShowChat(false)} className="text-zinc-500 hover:text-white">
                           <X className="w-4 h-4" />
                        </button>
                     </div>

                     {/* Chat Messages */}
                     <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-zinc-800">
                        {chatMessages.map((msg, idx) => (
                           <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                              <div className={`max-w-[85%] p-3 rounded-lg text-xs font-mono leading-relaxed ${
                                 msg.role === 'user' 
                                 ? 'bg-rose-900/20 border border-rose-500/20 text-rose-100 rounded-tr-none' 
                                 : 'bg-zinc-900 border border-zinc-800 text-zinc-300 rounded-tl-none'
                              }`}>
                                 {msg.text}
                              </div>
                           </div>
                        ))}
                        {isChatLoading && (
                           <div className="flex justify-start">
                              <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-lg rounded-tl-none">
                                 <div className="flex gap-1">
                                    <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" />
                                    <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce delay-100" />
                                    <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce delay-200" />
                                 </div>
                              </div>
                           </div>
                        )}
                        <div ref={chatEndRef} />
                     </div>

                     {/* Chat Input */}
                     <div className="p-4 border-t border-white/5 bg-black">
                        <form onSubmit={handleSendMessage} className="relative">
                           <input
                             type="text"
                             value={chatInput}
                             onChange={(e) => setChatInput(e.target.value)}
                             placeholder="Query the system..."
                             className="w-full bg-zinc-900 border border-zinc-800 rounded-lg pl-4 pr-10 py-3 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-rose-500/50"
                           />
                           <button 
                             type="submit" 
                             disabled={!chatInput.trim() || isChatLoading}
                             className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-zinc-400 hover:text-rose-500 disabled:opacity-50"
                           >
                              <SendIcon className="w-4 h-4" />
                           </button>
                        </form>
                     </div>
                 </div>
              </div>
           )}

        </div>
      </div>

      <style>{`
        @keyframes spin-slow { from { transform: translate(-50%, -50%) rotate(0deg); } to { transform: translate(-50%, -50%) rotate(360deg); } }
        .animate-spin-slow { animation: spin-slow 10s linear infinite; }
      `}</style>
    </div>
  );
}