import React, { useState, useRef, useEffect } from 'react';
import {
  Upload, FileText, CheckCircle, Download, Database, X, Layers, AlertCircle, Terminal as TerminalIcon, Zap
} from 'lucide-react';
import { apiFetch } from '../../api/client';
import { PageHeader, Card, Button } from '../../components/ui';

const ODOO_SLOTS = [
  { id: 'odoo_reg_cgst', label: 'Regular CGST' },
  { id: 'odoo_reg_igst', label: 'Regular IGST' },
  { id: 'odoo_rcm_cgst', label: 'RCM CGST' },
  { id: 'odoo_rcm_igst', label: 'RCM IGST' }
];

export default function RecoGSTR2B() {
  const [portalFile, setPortalFile] = useState(null);
  const [odooFiles, setOdooFiles] = useState({
    odoo_reg_cgst: null,
    odoo_reg_igst: null,
    odoo_rcm_cgst: null,
    odoo_rcm_igst: null
  });

  const [status, setStatus] = useState('idle');
  const [logs, setLogs] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const terminalRef = useRef(null);

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

  useEffect(() => {
    if (status === 'processing') {
      const steps = [
        "Initializing reconciliation engine…",
        "Reading GSTR-2B portal data…",
        "Scanning Odoo purchase registers…",
        "Merging regular & RCM data…",
        "Performing fuzzy matching logic…",
        "Generating reconciliation matrix…"
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
    if (!portalFile) {
      setErrorMessage("Please upload the Portal GSTR-2B file.");
      return;
    }

    const hasOdooFile = Object.values(odooFiles).some(f => f !== null);
    if (!hasOdooFile) {
      setErrorMessage("Please upload at least one Odoo register file.");
      return;
    }

    setStatus('processing');
    setErrorMessage('');

    const formData = new FormData();
    formData.append('file_portal', portalFile);
    Object.keys(odooFiles).forEach(key => {
      if (odooFiles[key]) formData.append(key, odooFiles[key]);
    });

    try {
      const response = await apiFetch('/api/indirect-tax/reco-gstr2b', {
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
      setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] SUCCESS: Reconciliation complete.`]);

    } catch (error) {
      setStatus('error');
      setErrorMessage(error.message);
      setLogs(prev => [...prev, `[ERROR] ${error.message}`]);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <PageHeader icon={Database} eyebrow="Indirect Tax" title="GSTR-2B Reconciliation" subtitle="Odoo vs Portal" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <h3 className="text-sm font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-amber-500/15 text-amber-400 flex items-center justify-center text-xs">1</span>
              Portal Data (GSTR-2B)
            </h3>

            {!portalFile ? (
              <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-white/[0.1] rounded-lg cursor-pointer hover:bg-white/[0.02] hover:border-amber-500/40 transition-colors group">
                <div className="flex items-center gap-3 text-neutral-500 group-hover:text-neutral-200">
                  <Upload className="w-5 h-5" />
                  <span className="text-sm font-medium">Upload GSTR-2B Excel</span>
                </div>
                <input type="file" className="hidden" accept=".xlsx, .xls" onChange={handlePortalChange} />
              </label>
            ) : (
              <div className="flex items-center justify-between p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-amber-400" />
                  <span className="text-sm font-medium text-neutral-200 truncate max-w-[250px]">{portalFile.name}</span>
                </div>
                <button onClick={() => removeFile('portal')} className="text-neutral-500 hover:text-red-400"><X className="w-4 h-4" /></button>
              </div>
            )}
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-amber-500/15 text-amber-400 flex items-center justify-center text-xs">2</span>
              Odoo Registers
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {ODOO_SLOTS.map((field) => (
                <div key={field.id} className="space-y-2">
                  <p className="text-xs font-medium text-neutral-500 uppercase">{field.label}</p>
                  {!odooFiles[field.id] ? (
                    <label className="flex items-center justify-center w-full h-12 border border-dashed border-white/[0.1] rounded-lg cursor-pointer hover:bg-white/[0.02] hover:border-amber-500/40 transition-colors">
                      <span className="text-xs text-neutral-500 flex items-center gap-2">
                        <Upload className="w-3 h-3" /> Select File
                      </span>
                      <input type="file" className="hidden" accept=".xlsx, .xls, .csv" onChange={(e) => handleOdooChange(field.id, e)} />
                    </label>
                  ) : (
                    <div className="flex items-center justify-between p-2 bg-neutral-800/60 border border-white/[0.08] rounded-lg">
                      <div className="flex items-center gap-2 overflow-hidden">
                        <Layers className="w-3 h-3 text-amber-400 flex-shrink-0" />
                        <span className="text-xs text-neutral-300 truncate">{odooFiles[field.id].name}</span>
                      </div>
                      <button onClick={() => removeFile('odoo', field.id)} className="text-neutral-500 hover:text-red-400"><X className="w-3 h-3" /></button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          {errorMessage && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3 text-red-400 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div className="flex justify-center py-2">
            <Button icon={Zap} loading={status === 'processing'} onClick={handleRunReco}>
              {status === 'processing' ? 'Reconciling' : 'Run Reconciliation'}
            </Button>
          </div>

          <div className="flex-1 bg-black/40 rounded-xl border border-white/[0.06] overflow-hidden flex flex-col min-h-[250px]">
            <div className="px-4 py-2 border-b border-white/[0.06] bg-black/20 flex items-center gap-2">
              <TerminalIcon className="w-3 h-3 text-neutral-500" />
              <span className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider">Engine Logs</span>
            </div>
            <div ref={terminalRef} className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-2 custom-scrollbar">
              {logs.length === 0 && status === 'idle' && (
                <span className="text-neutral-700 italic">// Ready to reconcile…</span>
              )}
              {logs.map((log, i) => (
                <div key={i} className="text-amber-400/80 animate-in slide-in-from-left-2 fade-in duration-300">
                  <span className="text-neutral-700 mr-2">{">"}</span>
                  {log}
                </div>
              ))}
            </div>
          </div>

          {status === 'success' && downloadUrl && (
            <div className="animate-in slide-in-from-bottom-4 duration-500 p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl">
              <h4 className="text-emerald-400 font-semibold text-sm mb-1 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" /> Reconciliation Success
              </h4>
              <p className="text-neutral-500 text-xs mb-3">Report generated successfully.</p>
              <a
                href={downloadUrl}
                download={`GSTR2B_Reco_${new Date().toISOString().slice(0, 10)}.xlsx`}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 hover:bg-amber-400 text-neutral-950 text-xs font-semibold rounded-lg transition-colors"
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
