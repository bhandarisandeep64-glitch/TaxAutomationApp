import React, { useState } from 'react';
import { CreditCard, CheckCircle, Download, Calendar, FileSpreadsheet, X, Plus, Type, Zap } from 'lucide-react';
import { apiFetch } from '../../api/client';
import { PageHeader, Card, Button } from '../../components/ui';

export default function TdsChallan() {
  const [step, setStep] = useState(1); // 1: Upload, 2: Fill, 3: Done
  const [file, setFile] = useState(null);
  const [filePath, setFilePath] = useState('');
  const [groups, setGroups] = useState([]);
  const [inputs, setInputs] = useState({});
  const [reportName, setReportName] = useState('');

  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus('idle');
      setMessage('');
    }
  };

  const removeFile = () => {
    setFile(null);
    setStatus('idle');
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setStatus('processing');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await apiFetch('/api/direct-tax/challan/analyze', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      if (res.ok) {
        setGroups(data.groups);
        setFilePath(data.temp_file_path);
        setStep(2);
        setStatus('idle');
      } else {
        setStatus('error');
        setMessage(data.error);
      }
    } catch (err) {
      setStatus('error');
      setMessage('Connection failed');
    }
  };

  const handleUpdate = async () => {
    setStatus('processing');
    try {
      const res = await apiFetch('/api/direct-tax/challan/update', {
        method: 'POST',
        body: JSON.stringify({
          file_path: filePath,
          inputs: inputs,
          custom_name: reportName
        })
      });
      const data = await res.json();

      if (res.ok) {
        const fileRes = await apiFetch(data.download_url);
        const blob = await fileRes.blob();
        setDownloadUrl(window.URL.createObjectURL(blob));
        setStep(3);
        setStatus('success');
      } else {
        setStatus('error');
        setMessage(data.error);
      }
    } catch (err) {
      setStatus('error');
      setMessage('Connection failed');
    }
  };

  const handleInputChange = (groupKey, field, value) => {
    setInputs(prev => ({
      ...prev,
      [groupKey]: { ...prev[groupKey], [field]: value }
    }));
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      <PageHeader icon={CreditCard} eyebrow="Direct Tax" title="Challan Payment Mapper" />

      {step === 1 && (
        <Card>
          <div className="flex flex-col md:flex-row gap-8 items-center">
            <div className="flex-1 w-full space-y-4">
              <div className="relative">
                <input type="file" id="challan-upload" className="hidden" accept=".xlsx, .csv" onChange={handleFileChange} />
                <label
                  htmlFor="challan-upload"
                  className="cursor-pointer flex items-center justify-center gap-2 w-full px-4 py-4 rounded-xl border border-dashed border-white/[0.12] hover:border-amber-500/50 hover:bg-white/[0.02] transition-colors text-neutral-500 hover:text-neutral-200"
                >
                  <Plus className="w-5 h-5" />
                  <span className="text-sm font-medium">Select TDS File to Analyze</span>
                </label>
              </div>

              {file && (
                <div className="flex items-center gap-3 p-3 rounded-lg border border-white/[0.08] bg-neutral-800/60 text-sm text-neutral-300 animate-in zoom-in-95">
                  <div className="p-2 bg-neutral-700/60 rounded">
                    <FileSpreadsheet className="w-4 h-4 text-amber-400" />
                  </div>
                  <span className="truncate flex-1">{file.name}</span>
                  <button onClick={removeFile} className="p-1 hover:bg-red-500/10 hover:text-red-400 rounded transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            <div className="flex-shrink-0">
              <Button icon={Zap} loading={status === 'processing'} disabled={!file} onClick={handleAnalyze}>
                {status === 'processing' ? 'Analyzing' : 'Analyze File'}
              </Button>
              {status === 'error' && <p className="text-red-400 text-xs mt-2 text-center max-w-[180px]">{message}</p>}
            </div>
          </div>
        </Card>
      )}

      {step === 2 && (
        <div className="space-y-8 animate-in slide-in-from-right-8 duration-500">
          <div className="flex justify-end items-center gap-4">
            <div className="flex items-center gap-3 px-4 py-2 rounded-xl border border-white/[0.08] bg-black/30 focus-within:border-amber-500/60 transition-colors w-full max-w-xs">
              <Type className="w-4 h-4 text-neutral-600" />
              <input
                type="text"
                placeholder="Custom Name (Optional)"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                className="bg-transparent border-none outline-none text-neutral-100 w-full placeholder-neutral-600 text-sm"
              />
            </div>
          </div>

          <div className="space-y-6">
            {groups.map((grp, idx) => {
              const key = `${grp.Section}|${grp['Co./Non Co.']}`;
              return (
                <Card key={idx} padded={false} className="overflow-hidden">
                  <div className="px-6 py-4 bg-black/20 border-b border-white/[0.06] flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-semibold text-neutral-50">{grp.Section}</span>
                      <span className="text-neutral-700">•</span>
                      <span className="text-sm font-medium text-neutral-500 uppercase">{grp['Co./Non Co.']}</span>
                    </div>
                    <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wider">
                      Due: ₹{grp.Total_Tax_Pending.toLocaleString()}
                    </div>
                  </div>

                  <div className="p-6 grid grid-cols-1 md:grid-cols-6 gap-4">
                    <div className="md:col-span-1 space-y-1">
                      <label className="text-[10px] font-semibold text-neutral-500 uppercase">Challan No</label>
                      <input type="text" className="w-full bg-black/30 border border-white/[0.08] rounded-lg p-2.5 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors"
                        onChange={(e) => handleInputChange(key, 'challan_no', e.target.value)} />
                    </div>
                    <div className="md:col-span-1 space-y-1">
                      <label className="text-[10px] font-semibold text-neutral-500 uppercase">Date</label>
                      <div className="relative">
                        <input type="date" className="w-full bg-black/30 border border-white/[0.08] rounded-lg p-2.5 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors appearance-none"
                          onChange={(e) => handleInputChange(key, 'date', e.target.value)} />
                        <Calendar className="w-3.5 h-3.5 text-neutral-600 absolute right-3 top-3 pointer-events-none" />
                      </div>
                    </div>
                    <div className="md:col-span-1 space-y-1">
                      <label className="text-[10px] font-semibold text-neutral-500 uppercase">BSR Code</label>
                      <input type="text" className="w-full bg-black/30 border border-white/[0.08] rounded-lg p-2.5 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors"
                        onChange={(e) => handleInputChange(key, 'bsr', e.target.value)} />
                    </div>
                    <div className="md:col-span-1 space-y-1">
                      <label className="text-[10px] font-semibold text-neutral-500 uppercase">Amount</label>
                      <input type="number" className="w-full bg-black/30 border border-white/[0.08] rounded-lg p-2.5 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors"
                        onChange={(e) => handleInputChange(key, 'amount', e.target.value)} />
                    </div>
                    <div className="md:col-span-1 space-y-1">
                      <label className="text-[10px] font-semibold text-neutral-500 uppercase">Interest</label>
                      <input type="number" className="w-full bg-black/30 border border-white/[0.08] rounded-lg p-2.5 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors"
                        onChange={(e) => handleInputChange(key, 'interest', e.target.value)} />
                    </div>
                    <div className="md:col-span-1 space-y-1">
                      <label className="text-[10px] font-semibold text-neutral-500 uppercase">Total</label>
                      <input type="number" className="w-full bg-black/30 border border-white/[0.08] rounded-lg p-2.5 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/60 focus:ring-2 focus:ring-amber-500/20 transition-colors"
                        onChange={(e) => handleInputChange(key, 'total', e.target.value)} />
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>

          <div className="flex justify-end pt-4 pb-10">
            <Button icon={Zap} loading={status === 'processing'} onClick={handleUpdate}>
              {status === 'processing' ? 'Updating' : 'Update & Download'}
            </Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="p-12 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 text-center animate-in zoom-in-95">
          <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-semibold text-neutral-50 mb-2">Challans Mapped Successfully</h2>
          <p className="text-neutral-500 mb-8">Your file has been updated with the details provided.</p>
          <a href={downloadUrl} className="inline-flex items-center gap-2 px-8 py-3.5 bg-amber-500 hover:bg-amber-400 text-neutral-950 font-semibold rounded-xl transition-colors shadow-lg shadow-amber-500/10">
            <Download className="w-5 h-5" /> Download Updated File
          </a>
          <button onClick={() => { setStep(1); setFile(null); }} className="block mt-6 mx-auto text-neutral-500 hover:text-neutral-200 text-sm underline transition-colors">
            Process Another File
          </button>
        </div>
      )}
    </div>
  );
}
