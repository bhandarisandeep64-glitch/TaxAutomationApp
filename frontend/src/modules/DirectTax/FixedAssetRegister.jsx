import React, { useState, useEffect, useRef } from 'react';
import {
  Upload, FileText, CheckCircle, Download, Landmark, X, FileSpreadsheet, Terminal as TerminalIcon, Zap
} from 'lucide-react';
import { apiFetch } from '../../api/client';
import { PageHeader, Card, Button } from '../../components/ui';

export default function FixedAssetRegister() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, processing, success, error
  const [logs, setLogs] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [finalFileName, setFinalFileName] = useState('');

  const terminalRef = useRef(null);

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

  useEffect(() => {
    if (status === 'processing') {
      const steps = [
        "Initializing calculation engine…",
        "Reading asset data structure…",
        "Applying Income Tax 180-day rule…",
        "Calculating depreciation blocks…",
        "Generating closing WDV report…",
        "Finalizing output…"
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

  const handleRunEngine = async () => {
    if (!file) return;

    setStatus('processing');
    const formData = new FormData();
    formData.append('file_assets', file);

    try {
      const response = await apiFetch('/api/fixed-assets/calculate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Calculation Failed');

      await new Promise(r => setTimeout(r, 5000));

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      setDownloadUrl(url);
      setFinalFileName(`FAR_${new Date().toISOString().slice(0, 10)}.xlsx`);
      setStatus('success');
      setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] SUCCESS: Register generated.`]);

    } catch (error) {
      setStatus('error');
      setLogs(prev => [...prev, `[ERROR] ${error.message}`]);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      <PageHeader icon={Landmark} eyebrow="Direct Tax" title="Depreciation Calculator" subtitle="Income Tax" />

      <Card>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between p-4 rounded-xl bg-black/20 border border-white/[0.06]">
              <div className="flex items-center gap-3">
                <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
                <div>
                  <h3 className="text-sm font-semibold text-neutral-200">Standard Format Required</h3>
                  <p className="text-xs text-neutral-500">Download the template to avoid column errors.</p>
                </div>
              </div>
              <Button variant="secondary" onClick={downloadTemplate} className="text-xs">Download Template</Button>
            </div>

            <div>
              {!file ? (
                <div className="relative group">
                  <input type="file" id="far-upload" className="hidden" accept=".xlsx, .csv" onChange={handleFileChange} />
                  <label
                    htmlFor="far-upload"
                    className="cursor-pointer flex flex-col items-center justify-center gap-3 w-full h-32 rounded-xl border-2 border-dashed border-white/[0.1] hover:border-amber-500/50 hover:bg-white/[0.02] transition-colors"
                  >
                    <div className="p-3 rounded-full bg-neutral-800/60 group-hover:bg-amber-500/10 transition-colors">
                      <Upload className="w-5 h-5 text-neutral-500 group-hover:text-amber-400" />
                    </div>
                    <span className="text-sm font-medium text-neutral-500 group-hover:text-neutral-200">
                      Upload Asset Excel File
                    </span>
                  </label>
                </div>
              ) : (
                <div className="flex items-center justify-between p-4 rounded-xl border border-amber-500/20 bg-amber-500/5">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-amber-500/10">
                      <FileText className="w-5 h-5 text-amber-400" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-neutral-100">{file.name}</p>
                      <p className="text-xs text-amber-400/70">Ready for calculation</p>
                    </div>
                  </div>
                  <button onClick={removeFile} className="p-2 hover:bg-white/[0.06] rounded-full text-neutral-500 hover:text-red-400 transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div className="flex justify-center py-2">
              <Button icon={Zap} loading={status === 'processing'} disabled={!file} onClick={handleRunEngine}>
                {status === 'processing' ? 'Processing' : 'Run Engine'}
              </Button>
            </div>

            <div className="flex-1 bg-black/40 rounded-xl border border-white/[0.06] overflow-hidden flex flex-col min-h-[200px]">
              <div className="px-4 py-2 border-b border-white/[0.06] bg-black/20 flex items-center gap-2">
                <TerminalIcon className="w-3 h-3 text-neutral-500" />
                <span className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider">System Logs</span>
              </div>
              <div ref={terminalRef} className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-2 custom-scrollbar">
                {logs.length === 0 && status === 'idle' && (
                  <span className="text-neutral-700 italic">// Waiting for input…</span>
                )}
                {logs.map((log, i) => (
                  <div key={i} className="text-amber-400/80 animate-in slide-in-from-left-2 fade-in duration-300">
                    <span className="text-neutral-700 mr-2">{">"}</span>
                    {log}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {status === 'success' && downloadUrl && (
        <div className="animate-in slide-in-from-bottom-4 duration-700 bg-emerald-500/5 border border-emerald-500/20 rounded-2xl p-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-full">
              <CheckCircle className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-neutral-50">Calculation Complete</h3>
              <p className="text-sm text-neutral-500">Your Fixed Asset Register is ready.</p>
            </div>
          </div>
          <a
            href={downloadUrl}
            download={finalFileName}
            className="flex items-center gap-2 px-6 py-3 bg-amber-500 hover:bg-amber-400 text-neutral-950 text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-amber-500/10"
          >
            <Download className="w-4 h-4" />
            Download Report
          </a>
        </div>
      )}
    </div>
  );
}
