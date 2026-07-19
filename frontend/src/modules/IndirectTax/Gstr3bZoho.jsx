import React, { useState } from 'react';
import {
  Upload, FileText, CheckCircle, Download, Calculator, X, Calendar, AlertCircle, Zap, ChevronDown, ChevronRight, Keyboard, FileUp
} from 'lucide-react';
import { apiFetch } from '../../api/client';
import { PageHeader, Card, Button, UploadSlot } from '../../components/ui';

const GSTR1_SLOTS = [
  { key: 'file_invoice_details', title: '1. Invoice Details' },
  { key: 'file_credit_note_details', title: '2. Credit Note Details' },
  { key: 'file_invoice_credit_notes', title: '3. Inv/CN Headers' },
  { key: 'file_export_invoices', title: '4. Export Invoices' },
];

export default function Gstr3bZoho() {
  const [clientName, setClientName] = useState('');
  const [period, setPeriod] = useState('');
  const [gstr1Mode, setGstr1Mode] = useState('upload'); // 'upload' | 'manual'
  const [gstr1Files, setGstr1Files] = useState({
    file_invoice_details: null, file_credit_note_details: null,
    file_invoice_credit_notes: null, file_export_invoices: null,
  });
  const [manualSales, setManualSales] = useState({ taxable: '', igst: '', cgst: '', sgst: '' });
  const [portalFile, setPortalFile] = useState(null);
  const [zohoFile, setZohoFile] = useState(null);
  const [showOpeningItc, setShowOpeningItc] = useState(false);
  const [openingItc, setOpeningItc] = useState({ igst: '', cgst: '', sgst: '' });

  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);

  const handleGstr1Change = (key) => (e) => {
    if (e.target.files[0]) setGstr1Files(prev => ({ ...prev, [key]: e.target.files[0] }));
  };
  const removeGstr1File = (key) => setGstr1Files(prev => ({ ...prev, [key]: null }));

  const handleRun = async () => {
    if (!clientName.trim()) { setStatus('error'); setMessage('Client name is required.'); return; }
    if (!period) { setStatus('error'); setMessage('Period is required.'); return; }
    if (gstr1Mode === 'upload' && !Object.values(gstr1Files).some(f => f)) { setStatus('error'); setMessage("At least one GSTR-1 header file ('Inv/CN Headers' or 'Export Invoices') is required (or switch to manual entry)."); return; }
    if (!portalFile) { setStatus('error'); setMessage('GSTR-2B portal file is required.'); return; }
    if (!zohoFile) { setStatus('error'); setMessage('Zoho Books file is required.'); return; }

    setStatus('processing');
    setMessage('');

    const formData = new FormData();
    formData.append('client_name', clientName.trim());
    formData.append('period', period);
    if (gstr1Mode === 'manual') {
      formData.append('gstr1_manual', JSON.stringify({
        taxable: parseFloat(manualSales.taxable) || 0,
        igst: parseFloat(manualSales.igst) || 0,
        cgst: parseFloat(manualSales.cgst) || 0,
        sgst: parseFloat(manualSales.sgst) || 0,
      }));
    } else {
      Object.keys(gstr1Files).forEach(key => { if (gstr1Files[key]) formData.append(key, gstr1Files[key]); });
    }
    formData.append('file_portal', portalFile);
    formData.append('file_zoho', zohoFile);
    if (showOpeningItc) {
      if (openingItc.igst !== '') formData.append('opening_igst', openingItc.igst);
      if (openingItc.cgst !== '') formData.append('opening_cgst', openingItc.cgst);
      if (openingItc.sgst !== '') formData.append('opening_sgst', openingItc.sgst);
    }

    try {
      const response = await apiFetch('/api/indirect-tax/gstr3b-zoho', { method: 'POST', body: formData });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || 'GSTR-3B generation failed.');
      }
      const blob = await response.blob();
      setDownloadUrl(window.URL.createObjectURL(blob));
      setStatus('success');
    } catch (error) {
      setStatus('error');
      setMessage(error.message || 'Failed to connect to the backend.');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      <PageHeader icon={Calculator} eyebrow="Indirect Tax" title="GSTR-3B Working Paper" subtitle="Zoho" />

      <Card>
        <h3 className="text-sm font-semibold text-neutral-200 mb-4 flex items-center gap-2">
          <span className="w-6 h-6 rounded bg-indigo-500/15 text-indigo-400 flex items-center justify-center text-xs">1</span>
          Client &amp; Period
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-white/[0.08] bg-black/30 focus-within:border-indigo-500/60 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-colors">
            <input
              type="text"
              placeholder="Client Name"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              className="bg-transparent border-none outline-none text-neutral-100 w-full placeholder-neutral-600 text-sm font-medium"
            />
          </div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <Calendar className="w-4 h-4 text-neutral-500" />
            </div>
            <input
              type="month"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              onClick={(e) => { try { e.target.showPicker() } catch (err) { } }}
              className="w-full bg-black/30 border border-white/[0.08] text-neutral-100 text-sm rounded-lg py-3 pl-11 pr-4 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors cursor-pointer"
            />
          </div>
        </div>

        <button
          onClick={() => setShowOpeningItc(v => !v)}
          className="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-200 transition-colors mt-4"
        >
          {showOpeningItc ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          Override opening ITC (defaults to last period's closing balance for this client)
        </button>
        {showOpeningItc && (
          <div className="grid grid-cols-3 gap-3 mt-3">
            {['igst', 'cgst', 'sgst'].map((head) => (
              <div key={head} className="px-3 py-2 rounded-lg border border-white/[0.08] bg-black/20">
                <label className="text-[10px] font-semibold text-neutral-500 uppercase">{head}</label>
                <input
                  type="number"
                  placeholder="0.00"
                  value={openingItc[head]}
                  onChange={(e) => setOpeningItc(prev => ({ ...prev, [head]: e.target.value }))}
                  className="w-full bg-transparent text-sm text-neutral-100 outline-none placeholder-neutral-700"
                />
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-neutral-200 flex items-center gap-2">
                <span className="w-6 h-6 rounded bg-indigo-500/15 text-indigo-400 flex items-center justify-center text-xs">2</span>
                GSTR-1 Sales Data
              </h3>
              <div className="flex items-center gap-1 p-1 rounded-lg border border-white/[0.08] bg-black/20">
                <button
                  onClick={() => setGstr1Mode('upload')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${gstr1Mode === 'upload' ? 'bg-indigo-600 text-white' : 'text-neutral-500 hover:text-neutral-200'}`}
                >
                  <FileUp className="w-3.5 h-3.5" /> Upload Files
                </button>
                <button
                  onClick={() => setGstr1Mode('manual')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${gstr1Mode === 'manual' ? 'bg-indigo-600 text-white' : 'text-neutral-500 hover:text-neutral-200'}`}
                >
                  <Keyboard className="w-3.5 h-3.5" /> Enter Manually
                </button>
              </div>
            </div>

            {gstr1Mode === 'upload' ? (
              <div className="grid grid-cols-2 gap-4">
                {GSTR1_SLOTS.map(s => (
                  <UploadSlot key={s.key} title={s.title} file={gstr1Files[s.key]} onChange={handleGstr1Change(s.key)} onRemove={() => removeGstr1File(s.key)} />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-[11px] text-neutral-500 -mt-1 mb-2">
                  Enter this period's total sales figures (feeds the Master Dashboard's Output Liability row).
                </p>
                <div className="grid grid-cols-4 gap-3">
                  {['taxable', 'igst', 'cgst', 'sgst'].map((field) => (
                    <div key={field} className="px-3 py-2 rounded-lg border border-white/[0.08] bg-black/20">
                      <label className="text-[10px] font-semibold text-neutral-500 uppercase">{field}</label>
                      <input
                        type="number"
                        placeholder="0.00"
                        value={manualSales[field]}
                        onChange={(e) => setManualSales(prev => ({ ...prev, [field]: e.target.value }))}
                        className="w-full bg-transparent text-sm text-neutral-100 outline-none placeholder-neutral-700"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-indigo-500/15 text-indigo-400 flex items-center justify-center text-xs">3</span>
              GSTR-2B Portal Data
            </h3>
            {!portalFile ? (
              <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-white/[0.1] rounded-lg cursor-pointer hover:bg-white/[0.02] hover:border-indigo-500/40 transition-colors group">
                <div className="flex items-center gap-3 text-neutral-500 group-hover:text-neutral-200">
                  <Upload className="w-5 h-5" />
                  <span className="text-sm font-medium">Upload GSTR-2B Excel</span>
                </div>
                <input type="file" className="hidden" accept=".xlsx, .xls" onChange={(e) => e.target.files[0] && setPortalFile(e.target.files[0])} />
              </label>
            ) : (
              <div className="flex items-center justify-between p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  <span className="text-sm font-medium text-neutral-200 truncate max-w-[250px]">{portalFile.name}</span>
                </div>
                <button onClick={() => setPortalFile(null)} className="text-neutral-500 hover:text-red-400"><X className="w-4 h-4" /></button>
              </div>
            )}
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-indigo-500/15 text-indigo-400 flex items-center justify-center text-xs">4</span>
              Zoho Books Data
            </h3>
            {!zohoFile ? (
              <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-white/[0.1] rounded-lg cursor-pointer hover:bg-white/[0.02] hover:border-indigo-500/40 transition-colors group">
                <div className="flex items-center gap-3 text-neutral-500 group-hover:text-neutral-200">
                  <Upload className="w-5 h-5" />
                  <span className="text-sm font-medium">Upload Zoho Books Excel</span>
                </div>
                <input type="file" className="hidden" accept=".xlsx, .xls" onChange={(e) => e.target.files[0] && setZohoFile(e.target.files[0])} />
              </label>
            ) : (
              <div className="flex items-center justify-between p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  <span className="text-sm font-medium text-neutral-200 truncate max-w-[250px]">{zohoFile.name}</span>
                </div>
                <button onClick={() => setZohoFile(null)} className="text-neutral-500 hover:text-red-400"><X className="w-4 h-4" /></button>
              </div>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          {status === 'error' && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3 text-red-400 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{message}</span>
            </div>
          )}

          <div className="flex justify-center py-2">
            <Button icon={Zap} loading={status === 'processing'} onClick={handleRun}>
              {status === 'processing' ? 'Generating' : 'Generate 3B Working'}
            </Button>
          </div>

          {status === 'success' && downloadUrl && (
            <div className="animate-in slide-in-from-bottom-4 duration-500 p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-lg">
              <h4 className="text-emerald-400 font-semibold text-sm mb-1 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" /> Working Paper Ready
              </h4>
              <p className="text-neutral-500 text-xs mb-3">Master Dashboard, Vendor Summary, and reconciliation detail sheets included.</p>
              <a
                href={downloadUrl}
                download={`${clientName || 'Client'} GSTR3B ${period}.xlsx`}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-colors"
              >
                <Download className="w-3 h-3" /> Download
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
