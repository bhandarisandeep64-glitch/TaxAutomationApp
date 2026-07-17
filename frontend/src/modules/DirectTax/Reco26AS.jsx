import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, Download, Type, Zap, X, FileJson } from 'lucide-react';
import { apiFetch } from '../../api/client';
import { PageHeader, Card, Button } from '../../components/ui';

export default function Reco26AS() {
  const [file, setFile] = useState(null);
  const [reportName, setReportName] = useState('');
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [finalFileName, setFinalFileName] = useState('');
  const [summaryData, setSummaryData] = useState([]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus('idle');
      setMessage('');
      setDownloadUrl(null);
      setSummaryData([]);
    }
  };

  const removeFile = () => {
    setFile(null);
    setStatus('idle');
  };

  const handleRunAutomation = async () => {
    if (!file) return;

    setStatus('processing');
    const formData = new FormData();
    formData.append('portal_file', file);
    formData.append('custom_name', reportName);

    try {
      const response = await apiFetch('/api/direct-tax/26as-reco', {
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
        setFinalFileName(data.filename || '26AS_Converted.xlsx');
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
      <PageHeader icon={FileJson} eyebrow="Direct Tax" title="26AS Converter" subtitle="TRACES" />

      <Card>
        <div className="flex flex-col md:flex-row gap-8 items-center">
          <div className="flex-1 w-full space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-white/[0.08] bg-black/30 focus-within:border-amber-500/60 focus-within:ring-2 focus-within:ring-amber-500/20 transition-colors">
                <Type className="w-4 h-4 text-neutral-600" />
                <input
                  type="text"
                  placeholder="Report Name (e.g. FY 24-25 Q3)"
                  value={reportName}
                  onChange={(e) => setReportName(e.target.value)}
                  className="bg-transparent border-none outline-none text-neutral-100 w-full placeholder-neutral-600 text-sm font-medium"
                />
              </div>

              <div className="relative">
                <input type="file" id="26as-upload" className="hidden" accept=".txt, .html" onChange={handleFileChange} />
                <label
                  htmlFor="26as-upload"
                  className="cursor-pointer flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl border border-dashed border-white/[0.12] hover:border-amber-500/50 hover:bg-white/[0.02] transition-colors text-neutral-500 hover:text-neutral-200"
                >
                  <Upload className="w-4 h-4" />
                  <span className="text-sm font-medium">Upload 26AS File</span>
                </label>
              </div>
            </div>

            {file && (
              <div className="flex items-center gap-3 p-3 rounded-lg border border-white/[0.08] bg-neutral-800/60 text-sm text-neutral-300 animate-in zoom-in-95 w-full md:w-1/2">
                <div className="p-2 bg-neutral-700/60 rounded">
                  <FileText className="w-4 h-4 text-amber-400" />
                </div>
                <span className="truncate flex-1">{file.name}</span>
                <button onClick={removeFile} className="p-1 hover:bg-red-500/10 hover:text-red-400 rounded transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          <div className="flex-shrink-0 self-center">
            <Button icon={Zap} loading={status === 'processing'} disabled={!file} onClick={handleRunAutomation}>
              {status === 'processing' ? 'Converting' : 'Convert'}
            </Button>
            {status === 'error' && <p className="text-red-400 text-xs mt-2 text-center max-w-[160px]">{message}</p>}
          </div>
        </div>
      </Card>

      {status === 'success' && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 animate-in slide-in-from-bottom-4 duration-700">
          <Card className="md:col-span-1 flex flex-col items-center justify-center text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-emerald-500" />
            <CheckCircle className="w-10 h-10 text-emerald-400 mb-3" />
            <h3 className="text-lg font-semibold text-neutral-50 mb-1">Converted</h3>
            <a href={downloadUrl} download={finalFileName} className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 hover:bg-amber-400 text-neutral-950 text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-amber-500/10">
              <Download className="w-4 h-4" /> Download Excel
            </a>
          </Card>

          <Card className="md:col-span-3" padded={false}>
            <div className="px-6 py-4 border-b border-white/[0.06]">
              <h3 className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">26AS Summary</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-black/20 text-neutral-500 text-xs uppercase">
                  <tr>
                    <th className="p-4 font-medium">Description</th>
                    <th className="p-4 text-right font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {summaryData.map((row, idx) => (
                    <tr key={idx} className="transition-colors hover:bg-white/[0.02]">
                      <td className="p-4 text-neutral-300">{row.Category}</td>
                      <td className="p-4 text-right font-mono font-semibold text-amber-400">₹{row.Amount?.toLocaleString()}</td>
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
