import React, { useState } from 'react';
import { CheckCircle, Download, Type, Zap, Layers } from 'lucide-react';
import { apiFetch } from '../../api/client';
import { PageHeader, Card, Button, UploadSlot } from '../../components/ui';

const SLOTS = [
  { key: 'regular_cgst', title: 'Regular CGST' },
  { key: 'regular_igst', title: 'Regular IGST' },
  { key: 'rcm_cgst', title: 'RCM CGST' },
  { key: 'rcm_igst', title: 'RCM IGST' },
];

export default function Gstr2bOdoo() {
  const [files, setFiles] = useState({
    regular_cgst: null,
    regular_igst: null,
    rcm_cgst: null,
    rcm_igst: null
  });

  const [reportName, setReportName] = useState('');
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [finalFileName, setFinalFileName] = useState('');
  const [summaryData, setSummaryData] = useState([]);

  const handleFileChange = (slot) => (e) => {
    if (e.target.files && e.target.files[0]) {
      setFiles(prev => ({ ...prev, [slot]: e.target.files[0] }));
      setStatus('idle');
      setMessage('');
      setDownloadUrl(null);
      setSummaryData([]);
    }
  };

  const removeFile = (slot) => {
    setFiles(prev => ({ ...prev, [slot]: null }));
    setStatus('idle');
  };

  const handleRunAutomation = async () => {
    if (!Object.values(files).some(f => f !== null)) {
      setMessage("Please upload at least one file.");
      setStatus('error');
      return;
    }

    setStatus('processing');
    const formData = new FormData();
    Object.keys(files).forEach(key => {
      if (files[key]) formData.append(key, files[key]);
    });
    formData.append('custom_name', reportName);

    try {
      const response = await apiFetch('/api/indirect-tax/gstr2b-odoo', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (response.ok) {
        setStatus('success');
        setMessage(data.message);
        const fileRes = await apiFetch(data.download_url);
        const blob = await fileRes.blob();
        setDownloadUrl(window.URL.createObjectURL(blob));
        setFinalFileName(data.filename || 'GSTR2B_Odoo_Processed.xlsx');
        setSummaryData(data.summary_data || []);
      } else {
        setStatus('error');
        setMessage(data.error || 'Server Error');
      }
    } catch (error) {
      setStatus('error');
      setMessage('Failed to connect to the backend.');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      <PageHeader icon={Layers} eyebrow="Indirect Tax" title="GSTR-2B Processing" subtitle="Odoo" />

      <Card>
        <div className="mb-6 max-w-md">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-white/[0.08] bg-black/30 focus-within:border-indigo-500/60 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-colors">
            <Type className="w-4 h-4 text-neutral-600" />
            <input
              type="text"
              placeholder="Report Name (e.g. Oct 2025 Purchase)"
              value={reportName}
              onChange={(e) => setReportName(e.target.value)}
              className="bg-transparent border-none outline-none text-neutral-100 w-full placeholder-neutral-600 text-sm font-medium"
            />
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 items-center">
          <div className="flex-1 w-full grid grid-cols-2 md:grid-cols-4 gap-4">
            {SLOTS.map(s => (
              <UploadSlot key={s.key} title={s.title} file={files[s.key]} onChange={handleFileChange(s.key)} onRemove={() => removeFile(s.key)} />
            ))}
          </div>

          <div className="flex-shrink-0 self-center">
            <Button icon={Zap} loading={status === 'processing'} disabled={!Object.values(files).some(f => f)} onClick={handleRunAutomation}>
              {status === 'processing' ? 'Processing' : 'Process Registers'}
            </Button>
            {status === 'error' && <p className="text-red-400 text-xs mt-2 text-center max-w-[180px]">{message}</p>}
          </div>
        </div>
      </Card>

      {status === 'success' && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 animate-in slide-in-from-bottom-4 duration-700">
          <Card className="md:col-span-1 flex flex-col items-center justify-center text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-emerald-500" />
            <CheckCircle className="w-10 h-10 text-emerald-400 mb-3" />
            <h3 className="text-lg font-semibold text-neutral-50 mb-1">Ready</h3>
            <a href={downloadUrl} download={finalFileName} className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg transition-colors shadow-lg shadow-indigo-500/10">
              <Download className="w-4 h-4" /> Download Excel
            </a>
          </Card>

          <Card className="md:col-span-3" padded={false}>
            <div className="px-6 py-4 border-b border-white/[0.06]">
              <h3 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Purchase Summary</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-black/20 text-neutral-500 text-xs uppercase">
                  <tr>
                    <th className="p-4 font-medium">Category</th>
                    <th className="p-4 text-right font-medium">Taxable Value</th>
                    <th className="p-4 text-right font-medium">IGST</th>
                    <th className="p-4 text-right font-medium">CGST</th>
                    <th className="p-4 text-right font-medium">SGST</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {summaryData.map((row, idx) => (
                    <tr key={idx} className={`transition-colors hover:bg-white/[0.02] ${row.Category === 'Total' ? 'font-semibold bg-black/10 text-indigo-400' : 'text-neutral-300'}`}>
                      <td className="p-4">{row.Category}</td>
                      <td className="p-4 text-right font-mono">₹{row.Taxable?.toLocaleString()}</td>
                      <td className="p-4 text-right font-mono">₹{row.IGST?.toLocaleString()}</td>
                      <td className="p-4 text-right font-mono">₹{row.CGST?.toLocaleString()}</td>
                      <td className="p-4 text-right font-mono">₹{row.SGST?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
