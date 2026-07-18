import React, { useState } from 'react';
import {
  Upload, FileText, CheckCircle, Download, Calculator, X, Plus, Calendar, AlertCircle, Zap, ChevronDown, ChevronRight, Keyboard, FileUp
} from 'lucide-react';
import { apiFetch } from '../../api/client';
import { PageHeader, Card, Button, UploadSlot } from '../../components/ui';

const ODOO_SLOTS = [
  { id: 'odoo_reg_cgst', label: 'Regular CGST' },
  { id: 'odoo_reg_igst', label: 'Regular IGST' },
  { id: 'odoo_rcm_cgst', label: 'RCM CGST' },
  { id: 'odoo_rcm_igst', label: 'RCM IGST' },
];

const GSTR1_MANUAL_CATEGORIES = ['B2B', 'B2B CDNR', 'B2C', 'B2C CDNR'];
const emptyManualGstr1 = () => Object.fromEntries(
  GSTR1_MANUAL_CATEGORIES.map(cat => [cat, { taxable: '', igst: '', cgst: '', sgst: '' }])
);

export default function Gstr3bOdoo() {
  const [clientName, setClientName] = useState('');
  const [period, setPeriod] = useState('');
  const [gstr1Mode, setGstr1Mode] = useState('upload'); // 'upload' | 'manual'
  const [gstr1Files, setGstr1Files] = useState([]);
  const [manualGstr1, setManualGstr1] = useState(emptyManualGstr1());
  const [portalFile, setPortalFile] = useState(null);
  const [odooFiles, setOdooFiles] = useState({
    odoo_reg_cgst: null, odoo_reg_igst: null, odoo_rcm_cgst: null, odoo_rcm_igst: null,
  });
  const [showOpeningItc, setShowOpeningItc] = useState(false);
  const [openingItc, setOpeningItc] = useState({ igst: '', cgst: '', sgst: '' });

  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);

  const handleGstr1FileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setGstr1Files(prev => [...prev, ...Array.from(e.target.files)]);
      setStatus('idle');
    }
  };
  const removeGstr1File = (index) => setGstr1Files(prev => prev.filter((_, i) => i !== index));

  const handleManualGstr1Change = (cat, field) => (e) => {
    setManualGstr1(prev => ({ ...prev, [cat]: { ...prev[cat], [field]: e.target.value } }));
  };

  const handleOdooChange = (key) => (e) => {
    if (e.target.files[0]) setOdooFiles(prev => ({ ...prev, [key]: e.target.files[0] }));
  };
  const removeOdooFile = (key) => setOdooFiles(prev => ({ ...prev, [key]: null }));

  const handleRun = async () => {
    if (!clientName.trim()) { setStatus('error'); setMessage('Client name is required.'); return; }
    if (!period) { setStatus('error'); setMessage('Period is required.'); return; }
    if (gstr1Mode === 'upload' && gstr1Files.length === 0) { setStatus('error'); setMessage('At least one GSTR-1 Odoo file is required (or switch to manual entry).'); return; }
    if (!portalFile) { setStatus('error'); setMessage('GSTR-2B portal file is required.'); return; }
    if (!Object.values(odooFiles).some(f => f)) { setStatus('error'); setMessage('At least one Odoo purchase register is required.'); return; }

    setStatus('processing');
    setMessage('');

    const formData = new FormData();
    formData.append('client_name', clientName.trim());
    formData.append('period', period);
    if (gstr1Mode === 'manual') {
      const payload = {};
      GSTR1_MANUAL_CATEGORIES.forEach(cat => {
        const row = manualGstr1[cat];
        payload[cat] = {
          taxable: parseFloat(row.taxable) || 0,
          igst: parseFloat(row.igst) || 0,
          cgst: parseFloat(row.cgst) || 0,
          sgst: parseFloat(row.sgst) || 0,
        };
      });
      formData.append('gstr1_manual', JSON.stringify(payload));
    } else {
      gstr1Files.forEach(f => formData.append('gstr1_files', f));
    }
    formData.append('file_portal', portalFile);
    Object.keys(odooFiles).forEach(key => { if (odooFiles[key]) formData.append(key, odooFiles[key]); });
    if (showOpeningItc) {
      if (openingItc.igst !== '') formData.append('opening_igst', openingItc.igst);
      if (openingItc.cgst !== '') formData.append('opening_cgst', openingItc.cgst);
      if (openingItc.sgst !== '') formData.append('opening_sgst', openingItc.sgst);
    }

    try {
      const response = await apiFetch('/api/indirect-tax/gstr3b-odoo', { method: 'POST', body: formData });
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
      <PageHeader icon={Calculator} eyebrow="Indirect Tax" title="GSTR-3B Working Paper" subtitle="Odoo" />

      <Card>
        <h3 className="text-sm font-semibold text-neutral-200 mb-4 flex items-center gap-2">
          <span className="w-6 h-6 rounded bg-amber-500/15 text-amber-400 flex items-center justify-center text-xs">1</span>
          Client &amp; Period
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-white/[0.08] bg-black/30 focus-within:border-amber-500/60 focus-within:ring-2 focus-within:ring-amber-500/20 transition-colors">
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
              className="w-full bg-black/30 border border-white/[0.08] text-neutral-100 text-sm rounded-xl py-3 pl-11 pr-4 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors cursor-pointer"
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
                <span className="w-6 h-6 rounded bg-amber-500/15 text-amber-400 flex items-center justify-center text-xs">2</span>
                GSTR-1 Sales Data
              </h3>
              <div className="flex items-center gap-1 p-1 rounded-lg border border-white/[0.08] bg-black/20">
                <button
                  onClick={() => setGstr1Mode('upload')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${gstr1Mode === 'upload' ? 'bg-amber-500 text-neutral-950' : 'text-neutral-500 hover:text-neutral-200'}`}
                >
                  <FileUp className="w-3.5 h-3.5" /> Upload Files
                </button>
                <button
                  onClick={() => setGstr1Mode('manual')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${gstr1Mode === 'manual' ? 'bg-amber-500 text-neutral-950' : 'text-neutral-500 hover:text-neutral-200'}`}
                >
                  <Keyboard className="w-3.5 h-3.5" /> Enter Manually
                </button>
              </div>
            </div>

            {gstr1Mode === 'upload' ? (
              <>
                <div className="relative mb-3">
                  <input type="file" id="gstr1-upload" className="hidden" multiple accept=".xlsx, .csv" onChange={handleGstr1FileChange} />
                  <label
                    htmlFor="gstr1-upload"
                    className="cursor-pointer flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl border border-dashed border-white/[0.12] hover:border-amber-500/50 hover:bg-white/[0.02] transition-colors text-neutral-500 hover:text-neutral-200"
                  >
                    <Plus className="w-4 h-4" />
                    <span className="text-sm font-medium">Add Sales/CDNR Ledger Files</span>
                  </label>
                </div>
                {gstr1Files.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {gstr1Files.map((file, index) => (
                      <div key={index} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/[0.08] bg-neutral-800/60 text-xs text-neutral-300 animate-in zoom-in-95">
                        <FileText className="w-3 h-3 text-amber-400" />
                        <span className="truncate max-w-[150px]">{file.name}</span>
                        <button onClick={() => removeGstr1File(index)} className="hover:text-red-400"><X className="w-3 h-3" /></button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="space-y-3">
                <p className="text-[11px] text-neutral-500 -mt-1 mb-2">
                  Enter the GSTR-1 SUMMARY totals as you've already worked them out (same 4 categories as the working paper).
                </p>
                <div className="overflow-x-auto -mx-1">
                  <table className="w-full text-sm min-w-[520px]">
                    <thead>
                      <tr className="text-[10px] text-neutral-500 uppercase">
                        <th className="text-left font-medium px-1 pb-2">Nature</th>
                        <th className="text-right font-medium px-1 pb-2">Taxable Value</th>
                        <th className="text-right font-medium px-1 pb-2">IGST</th>
                        <th className="text-right font-medium px-1 pb-2">CGST</th>
                        <th className="text-right font-medium px-1 pb-2">SGST</th>
                      </tr>
                    </thead>
                    <tbody>
                      {GSTR1_MANUAL_CATEGORIES.map(cat => (
                        <tr key={cat}>
                          <td className="px-1 py-1 text-xs font-medium text-neutral-300 whitespace-nowrap">{cat}</td>
                          {['taxable', 'igst', 'cgst', 'sgst'].map(field => (
                            <td key={field} className="px-1 py-1">
                              <input
                                type="number"
                                placeholder="0.00"
                                value={manualGstr1[cat][field]}
                                onChange={handleManualGstr1Change(cat, field)}
                                className="w-full bg-black/30 border border-white/[0.08] rounded-lg px-2 py-1.5 text-right text-sm text-neutral-100 outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors placeholder-neutral-700"
                              />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-amber-500/15 text-amber-400 flex items-center justify-center text-xs">3</span>
              GSTR-2B Portal Data
            </h3>
            {!portalFile ? (
              <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-white/[0.1] rounded-lg cursor-pointer hover:bg-white/[0.02] hover:border-amber-500/40 transition-colors group">
                <div className="flex items-center gap-3 text-neutral-500 group-hover:text-neutral-200">
                  <Upload className="w-5 h-5" />
                  <span className="text-sm font-medium">Upload GSTR-2B Excel</span>
                </div>
                <input type="file" className="hidden" accept=".xlsx, .xls" onChange={(e) => e.target.files[0] && setPortalFile(e.target.files[0])} />
              </label>
            ) : (
              <div className="flex items-center justify-between p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-amber-400" />
                  <span className="text-sm font-medium text-neutral-200 truncate max-w-[250px]">{portalFile.name}</span>
                </div>
                <button onClick={() => setPortalFile(null)} className="text-neutral-500 hover:text-red-400"><X className="w-4 h-4" /></button>
              </div>
            )}
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-amber-500/15 text-amber-400 flex items-center justify-center text-xs">4</span>
              GSTR-2B Odoo Purchase Registers
            </h3>
            <div className="grid grid-cols-2 gap-4">
              {ODOO_SLOTS.map(s => (
                <UploadSlot key={s.id} title={s.label} file={odooFiles[s.id]} onChange={handleOdooChange(s.id)} onRemove={() => removeOdooFile(s.id)} />
              ))}
            </div>
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
            <div className="animate-in slide-in-from-bottom-4 duration-500 p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl">
              <h4 className="text-emerald-400 font-semibold text-sm mb-1 flex items-center gap-2">
                <CheckCircle className="w-4 h-4" /> Working Paper Ready
              </h4>
              <p className="text-neutral-500 text-xs mb-3">3B SUMMARY, GSTR2B SUMMARY, GSTR1 SUMMARY, and reconciliation detail sheets included.</p>
              <a
                href={downloadUrl}
                download={`${clientName || 'Client'} GSTR3B ${period}.xlsx`}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 hover:bg-amber-400 text-neutral-950 text-xs font-semibold rounded-lg transition-colors"
              >
                <Download className="w-3 h-3" /> Download
              </a>
            </div>
          )}

          <p className="text-[11px] text-neutral-600 leading-relaxed px-1">
            The "NOT CLAIMED WORKING" sheet in the output is a blank template for your own manual carry-forward review, same as your existing process.
          </p>
        </div>
      </div>
    </div>
  );
}
