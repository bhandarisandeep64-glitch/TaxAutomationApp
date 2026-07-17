import React, { useState, useRef, useEffect } from 'react';
import {
  Upload, FileText, CheckCircle, Download, Database, X,
  AlertCircle, Terminal as TerminalIcon,
  TrendingUp, Wallet, Calendar, Sparkles, Bot,
  Send as SendIcon, Loader, Settings, Key, Lock, Zap
} from 'lucide-react';
import { apiFetch } from '../../api/client';
import { PageHeader, Card, Button } from '../../components/ui';

export default function RecoGSTR2BZoho() {
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

  // --- AI ASSISTANT STATE ---
  const [showChat, setShowChat] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [userApiKey, setUserApiKey] = useState('');
  const [storedApiKey, setStoredApiKey] = useState('');

  const [chatMessages, setChatMessages] = useState([
    { role: 'ai', text: 'Hi, I\'m the Black Rose Tax Assistant. Ask me about GST reconciliation or this report.' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [aiSummary, setAiSummary] = useState(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    const savedKey = localStorage.getItem('BLACK_ROSE_API_KEY');
    if (savedKey) {
      setStoredApiKey(savedKey);
      setUserApiKey(savedKey);
    }
  }, []);

  const handleSaveSettings = () => {
    localStorage.setItem('BLACK_ROSE_API_KEY', userApiKey);
    setStoredApiKey(userApiKey);
    setShowSettings(false);
    setLogs(prev => [...prev, `[SYSTEM] AI Assistant key updated.`]);
  };

  const callGeminiAPI = async (prompt, systemInstruction = '') => {
    let apiKey = storedApiKey;
    if (!apiKey) {
      throw new Error("MISSING_KEY");
    }

    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`;

    const payload = {
      contents: [{ parts: [{ text: prompt }] }],
      systemInstruction: systemInstruction ? { parts: [{ text: systemInstruction }] } : undefined
    };

    let attempt = 0;
    const delays = [1000, 2000, 4000];

    while (attempt <= 3) {
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
        if (attempt === 3) throw err;
        await new Promise(r => setTimeout(r, delays[attempt]));
        attempt++;
      }
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput;
    setChatMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setChatInput('');
    setIsChatLoading(true);

    try {
      const systemPrompt = "You are 'Black Rose AI', a professional, precise tax automation assistant. You help users with Indian GST (GSTR-2B, ITC) and Zoho Books reconciliation queries. Keep answers under 80 words unless detailed explanation is requested.";
      const aiResponse = await callGeminiAPI(userMsg, systemPrompt);
      setChatMessages(prev => [...prev, { role: 'ai', text: aiResponse }]);
    } catch (error) {
      if (error.message === "MISSING_KEY") {
        setChatMessages(prev => [...prev, { role: 'ai', text: "No API key configured yet. Click the settings icon and add your Gemini API key to enable the assistant." }]);
      } else {
        setChatMessages(prev => [...prev, { role: 'ai', text: "Connection interrupted. Please try again." }]);
      }
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
      - Keep it brief (bullet points).`;

      const summary = await callGeminiAPI(prompt);
      setAiSummary(summary);
    } catch (error) {
      if (error.message === "MISSING_KEY") {
        setAiSummary("No API key configured. Add one in Settings to generate an AI summary.");
      } else {
        setAiSummary("Failed to generate summary.");
      }
    } finally {
      setIsSummarizing(false);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, showChat]);

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

  useEffect(() => {
    if (status === 'processing') {
      const steps = [
        "Initializing reconciliation engine…",
        "Reading GSTR-2B portal data…",
        "Scanning Zoho Books ledger…",
        "Normalizing data structures…",
        "Applying manual overrides & opening balances…",
        "Purging duplicate RCM entries…",
        "Executing fuzzy matching logic…",
        "Compiling reconciliation matrix…"
      ];
      let delay = 0;
      setLogs([]);
      steps.forEach((step) => {
        setTimeout(() => {
          setLogs(prev => [...prev, `[${new Date().toLocaleTimeString('en-US', { hour12: false })}] ${step}`]);
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
      setErrorMessage("Both source files are required.");
      return;
    }

    setStatus('processing');
    setErrorMessage('');
    setAiSummary(null);

    const formData = new FormData();
    formData.append('file_portal', portalFile);
    formData.append('file_zoho', zohoFile);

    Object.keys(inputs).forEach(key => {
      formData.append(key, inputs[key]);
    });

    try {
      const response = await apiFetch('/api/indirect-tax/reco-gstr2b-zoho', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Reconciliation Failed');
      }

      await new Promise(r => setTimeout(r, 6500));

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      setDownloadUrl(url);
      setStatus('success');
      setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] SUCCESS: Report generated.`]);

    } catch (error) {
      setStatus('error');
      setErrorMessage(error.message);
      setLogs(prev => [...prev, `[ERROR] ${error.message}`]);
    }
  };

  const FieldInput = ({ label, name, value, onChange, prefix }) => (
    <div className="group relative flex flex-col gap-1 bg-black/20 border border-white/[0.08] rounded-lg p-2 focus-within:border-amber-500/50 focus-within:bg-black/30 transition-colors hover:border-white/[0.12]">
      <label className="text-[9px] font-mono text-neutral-500 uppercase tracking-wider group-focus-within:text-amber-400 transition-colors">
        {label}
      </label>
      <div className="flex items-center w-full">
        {prefix && <span className="text-neutral-500 text-xs font-mono mr-1.5">{prefix}</span>}
        <input
          type="number"
          name={name}
          value={value}
          onChange={onChange}
          placeholder="0.00"
          className="w-full bg-transparent text-sm font-mono text-neutral-100 placeholder-neutral-700 focus:outline-none"
        />
      </div>
    </div>
  );

  const FileRow = ({ label, file, onFileChange, onRemove, icon: Icon }) => (
    <div className="flex items-center justify-between p-2.5 bg-black/30 border border-white/[0.06] rounded-lg transition-colors hover:border-amber-500/20 group">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md bg-amber-500/10 flex items-center justify-center border border-white/[0.05]">
          <Icon className="w-4 h-4 text-amber-400" />
        </div>
        <div className="flex flex-col">
          <span className="text-[9px] font-semibold text-neutral-500 uppercase tracking-widest">{label}</span>
          {file ? (
            <span className="text-xs font-medium text-neutral-100 truncate max-w-[140px] md:max-w-[200px] flex items-center gap-1.5">
              {file.name} <CheckCircle className="w-3 h-3 text-amber-400" />
            </span>
          ) : (
            <span className="text-xs text-neutral-700 italic">No file selected</span>
          )}
        </div>
      </div>

      {file ? (
        <button onClick={onRemove} className="p-1.5 rounded-md hover:bg-red-500/10 text-neutral-600 hover:text-red-400 transition-colors" title="Remove File">
          <X className="w-4 h-4" />
        </button>
      ) : (
        <label className="cursor-pointer">
          <input type="file" className="hidden" accept=".xlsx, .xls" onChange={onFileChange} />
          <div className="px-3 py-1.5 rounded bg-neutral-800/60 border border-white/[0.08] flex items-center gap-2 transition-colors hover:bg-neutral-700/60 hover:border-amber-500/30">
            <Upload className="w-3 h-3 text-neutral-400" />
            <span className="text-[10px] font-semibold text-neutral-400 uppercase">Load</span>
          </div>
        </label>
      )}
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500 relative">
      <PageHeader
        icon={Database}
        eyebrow="Indirect Tax"
        title="GSTR-2B Reconciliation"
        subtitle="Zoho vs Portal"
        action={
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSettings(true)}
              className={`p-2 rounded-full border transition-colors ${!storedApiKey ? 'bg-amber-500/10 border-amber-500/40 text-amber-400' : 'bg-neutral-900/50 border-white/[0.08] text-neutral-400 hover:border-white/[0.16] hover:text-neutral-100'}`}
              title="AI Assistant settings"
            >
              <Settings className="w-4 h-4" />
            </button>

            <button
              onClick={() => setShowChat(!showChat)}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-full border text-xs font-medium transition-colors ${showChat ? 'bg-amber-500/10 border-amber-500/40 text-amber-400' : 'bg-neutral-900/50 border-white/[0.08] text-neutral-400 hover:border-amber-500/30 hover:text-amber-400'}`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              {showChat ? 'Assistant Open' : 'AI Assistant'}
            </button>

            <div className={`px-4 py-1.5 rounded-full border text-xs font-medium flex items-center gap-2 ${status === 'processing' ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' :
                status === 'success' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                  status === 'error' ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                    'bg-neutral-900/50 border-white/[0.08] text-neutral-400'
              }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${status === 'processing' ? 'bg-amber-400 animate-ping' : status === 'success' ? 'bg-emerald-400' : status === 'error' ? 'bg-red-400' : 'bg-neutral-500'}`} />
              {status === 'idle' ? 'Ready' : status.charAt(0).toUpperCase() + status.slice(1)}
            </div>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 relative">

        <div className="lg:col-span-8 space-y-6">
          <Card>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded flex items-center justify-center bg-amber-500/15 text-amber-400 text-xs font-semibold">1</div>
                <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider">Source Files</h3>
              </div>
              <div className="relative group cursor-pointer w-40">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Calendar className="w-4 h-4 text-neutral-500 group-hover:text-amber-400 transition-colors" />
                </div>
                <input
                  type="month"
                  name="month"
                  value={inputs.month}
                  onChange={handleInputChange}
                  onClick={(e) => { try { e.target.showPicker() } catch (e) { } }}
                  className="bg-black/20 border border-white/[0.08] text-neutral-300 text-xs font-mono rounded-lg py-2 pl-10 pr-3 w-full focus:outline-none focus:border-amber-500/50 hover:border-white/[0.14] transition-colors cursor-pointer uppercase"
                />
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <FileRow
                label="GST Portal Data (XLSX)"
                file={portalFile}
                onFileChange={(e) => handleFileChange('portal', e)}
                onRemove={() => removeFile('portal')}
                icon={FileText}
              />
              <FileRow
                label="Zoho Books Data (XLSX)"
                file={zohoFile}
                onFileChange={(e) => handleFileChange('zoho', e)}
                onRemove={() => removeFile('zoho')}
                icon={Database}
              />
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-2 mb-6">
              <div className="w-5 h-5 rounded flex items-center justify-center bg-amber-500/15 text-amber-400 text-xs font-semibold">2</div>
              <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider">Manual Adjustments</h3>
              <div className="h-px flex-1 bg-white/[0.06] ml-4" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
              <div className="space-y-3">
                <div className="flex items-center gap-2 mb-1">
                  <TrendingUp className="w-3 h-3 text-amber-400" />
                  <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest">Outward Supplies</span>
                </div>
                <div className="space-y-2">
                  <FieldInput label="Taxable Value" name="sales_taxable" value={inputs.sales_taxable} onChange={handleInputChange} prefix="₹" />
                  <div className="grid grid-cols-3 gap-2">
                    <FieldInput label="IGST" name="sales_igst" value={inputs.sales_igst} onChange={handleInputChange} />
                    <FieldInput label="CGST" name="sales_cgst" value={inputs.sales_cgst} onChange={handleInputChange} />
                    <FieldInput label="SGST" name="sales_sgst" value={inputs.sales_sgst} onChange={handleInputChange} />
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2 mb-1">
                  <Wallet className="w-3 h-3 text-amber-400" />
                  <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest">Opening ITC</span>
                </div>
                <div className="space-y-2">
                  <FieldInput label="Opening IGST" name="op_igst" value={inputs.op_igst} onChange={handleInputChange} prefix="₹" />
                  <div className="grid grid-cols-2 gap-2">
                    <FieldInput label="Opening CGST" name="op_cgst" value={inputs.op_cgst} onChange={handleInputChange} prefix="₹" />
                    <FieldInput label="Opening SGST" name="op_sgst" value={inputs.op_sgst} onChange={handleInputChange} prefix="₹" />
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-4 flex flex-col gap-4">
          {errorMessage && (
            <div className="animate-in slide-in-from-right-4 fade-in duration-300 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-red-400 font-semibold text-[10px] uppercase tracking-wider">Error</h4>
                <p className="text-red-400/80 text-[10px] mt-0.5">{errorMessage}</p>
              </div>
            </div>
          )}

          <div className="flex justify-center py-2">
            <Button icon={Zap} loading={status === 'processing'} onClick={handleRunReco}>
              {status === 'processing' ? 'Reconciling' : 'Run Reconciliation'}
            </Button>
          </div>

          <div className="flex-1 bg-black/40 rounded-xl border border-white/[0.06] overflow-hidden flex flex-col min-h-[300px]">
            <div className="px-4 py-2 bg-black/20 border-b border-white/[0.06] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TerminalIcon className="w-3 h-3 text-amber-400" />
                <span className="text-[10px] font-mono text-neutral-500 uppercase tracking-widest">Activity Log</span>
              </div>
            </div>

            <div ref={terminalRef} className="flex-1 p-4 overflow-y-auto font-mono text-[10px] md:text-xs space-y-1.5 custom-scrollbar">
              {logs.length === 0 && status === 'idle' && (
                <div className="flex flex-col items-center justify-center h-full opacity-30 text-neutral-500 space-y-2">
                  <TerminalIcon className="w-8 h-8" />
                  <span>Waiting for input…</span>
                </div>
              )}
              {logs.map((log, i) => {
                const isError = log.includes("ERROR") || log.includes("FAILURE");
                const isSuccess = log.includes("SUCCESS");
                return (
                  <div key={i} className={`flex items-start gap-2 ${isError ? 'text-red-400' : isSuccess ? 'text-emerald-400' : 'text-neutral-400'} animate-in slide-in-from-left-2 fade-in duration-300`}>
                    <span className="opacity-50 shrink-0">{">"}</span>
                    <span className="break-all leading-relaxed">{log}</span>
                  </div>
                )
              })}
            </div>
          </div>

          {status === 'success' && downloadUrl && (
            <div className="space-y-4 animate-in slide-in-from-bottom-8 duration-700">
              {!aiSummary ? (
                <button
                  onClick={handleGenerateSummary}
                  disabled={isSummarizing}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10 text-amber-400 text-xs font-semibold transition-colors"
                >
                  {isSummarizing ? <Loader className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {isSummarizing ? 'Generating summary…' : 'Generate AI Executive Summary'}
                </button>
              ) : (
                <div className="p-4 bg-neutral-900/60 border border-white/[0.08] rounded-xl relative overflow-hidden animate-in fade-in duration-500">
                  <div className="absolute top-0 left-0 w-full h-1 bg-amber-500" />
                  <div className="flex items-center gap-2 mb-2">
                    <Bot className="w-4 h-4 text-amber-400" />
                    <h4 className="text-xs font-semibold text-neutral-100 uppercase tracking-wider">AI Executive Summary</h4>
                  </div>
                  <p className="text-[10px] md:text-xs text-neutral-300 leading-relaxed whitespace-pre-wrap">
                    {aiSummary}
                  </p>
                </div>
              )}

              <a
                href={downloadUrl}
                download={`Zoho_Reco_${new Date().toISOString().slice(0, 10)}.xlsx`}
                className="group w-full flex items-center justify-between p-1 pl-4 pr-1 bg-emerald-500/5 border border-emerald-500/20 hover:border-emerald-400/40 rounded-xl transition-colors"
              >
                <div className="flex flex-col">
                  <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">Report Ready</span>
                  <span className="text-xs text-neutral-300">Download Excel Analysis</span>
                </div>
                <div className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center group-hover:scale-105 transition-transform text-neutral-950">
                  <Download className="w-5 h-5" />
                </div>
              </a>
            </div>
          )}
        </div>

        {showSettings && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-300 p-4">
            <div className="w-full max-w-md bg-neutral-900 border border-white/[0.08] rounded-2xl shadow-2xl p-6 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-amber-500" />

              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                    <Settings className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-100">AI Assistant Settings</h3>
                    <p className="text-[10px] text-neutral-500">Connect a Google Gemini API key</p>
                  </div>
                </div>
                <button onClick={() => setShowSettings(false)} className="text-neutral-500 hover:text-neutral-200"><X className="w-5 h-5" /></button>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-mono text-neutral-400 uppercase tracking-widest ml-1 flex items-center gap-2">
                    <Key className="w-3 h-3" /> API Key
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="w-4 h-4 text-neutral-600" />
                    </div>
                    <input
                      type="password"
                      value={userApiKey}
                      onChange={(e) => setUserApiKey(e.target.value)}
                      placeholder="Paste Gemini API key here…"
                      className="w-full bg-black/30 border border-white/[0.08] rounded-xl pl-10 pr-4 py-3 text-xs text-neutral-100 placeholder-neutral-700 focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20 outline-none font-mono transition-colors"
                    />
                  </div>
                  <p className="text-[10px] text-neutral-600 pl-1">
                    Stored locally on your device only.
                  </p>
                </div>

                <Button onClick={handleSaveSettings} icon={CheckCircle} className="w-full">Save Key</Button>

                <div className="text-center pt-2">
                  <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" className="text-[10px] text-neutral-500 hover:text-amber-400 underline decoration-neutral-700 underline-offset-4 transition-colors">
                    Get a key from Google AI Studio
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}

        {showChat && (
          <div className="fixed top-0 right-0 w-full md:w-[380px] h-full z-50 animate-in slide-in-from-right duration-300 shadow-2xl">
            <div className="w-full h-full bg-neutral-950/95 backdrop-blur-xl border-l border-white/[0.08] flex flex-col">
              <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  <span className="text-sm font-semibold text-neutral-100">Tax Assistant</span>
                </div>
                <button onClick={() => setShowChat(false)} className="text-neutral-500 hover:text-neutral-200">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] p-3 rounded-xl text-xs leading-relaxed ${msg.role === 'user'
                        ? 'bg-amber-500/10 border border-amber-500/20 text-amber-100 rounded-tr-sm'
                        : 'bg-neutral-800/60 border border-white/[0.06] text-neutral-300 rounded-tl-sm'
                      }`}>
                      {msg.text}
                    </div>
                  </div>
                ))}
                {isChatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-neutral-800/60 border border-white/[0.06] p-3 rounded-xl rounded-tl-sm">
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce" />
                        <div className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce delay-100" />
                        <div className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce delay-200" />
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <div className="p-4 border-t border-white/[0.06]">
                <form onSubmit={handleSendMessage} className="relative">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask a question…"
                    className="w-full bg-black/30 border border-white/[0.08] rounded-xl pl-4 pr-10 py-3 text-xs text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors"
                  />
                  <button
                    type="submit"
                    disabled={!chatInput.trim() || isChatLoading}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-neutral-400 hover:text-amber-400 disabled:opacity-50 transition-colors"
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
  );
}
