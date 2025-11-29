import React, { useState } from 'react';
import { 
  Upload, 
  FileSpreadsheet, 
  CheckCircle, 
  AlertCircle, 
  Download, 
  Type, 
  Flower, 
  X,
  Plus
} from 'lucide-react';
import { THEME } from '../../constants/theme';

export default function TdsOdoo() {
  const [files, setFiles] = useState([]);
  const [reportName, setReportName] = useState('');
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [summaryData, setSummaryData] = useState([]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...newFiles]);
      setStatus('idle');
      setMessage('');
      setDownloadUrl(null);
      setSummaryData([]);
    }
  };

  const removeFile = (indexToRemove) => {
    setFiles(prev => prev.filter((_, index) => index !== indexToRemove));
    setStatus('idle');
  };

  const handleRunAutomation = async () => {
    if (files.length === 0) return;

    setStatus('processing');
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('custom_name', reportName);

    try {
      const response = await fetch('https://taxautomationapp.onrender.com/api/direct-tax/tds-odoo', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (response.ok) {
        setStatus('success');
        setMessage(data.message);
        setDownloadUrl(`https://taxautomationapp.onrender.com${data.download_url}`);
        setSummaryData(data.summary_data || []);
      } else {
        setStatus('error');
        setMessage(data.error || 'Server Error');
      }
    } catch (error) {
      setStatus('error');
      setMessage('Failed to connect to Python Backend.');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* HEADER (Compact) */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
        <FileSpreadsheet className={`w-6 h-6 ${THEME.accent}`} />
        <h2 className="text-xl font-bold text-white tracking-tight">TDS Automation <span className="text-slate-600">|</span> Odoo</h2>
      </div>

      {/* COMPACT CONTROL PANEL */}
      <div className={`p-5 rounded-2xl border ${THEME.border} bg-slate-900/50 shadow-xl`}>
        <div className="flex flex-col md:flex-row gap-6 items-start">
            
            {/* LEFT: Inputs (Flexible Width) */}
            <div className="flex-1 w-full space-y-4">
                
                {/* Row 1: Name & Add Button */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Name Input */}
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-slate-700 bg-slate-950 focus-within:border-amber-500 transition-colors">
                        <Type className="w-4 h-4 text-slate-500" />
                        <input 
                            type="text" 
                            placeholder="Report Name (e.g. 2025.11 VTI)" 
                            value={reportName}
                            onChange={(e) => setReportName(e.target.value)}
                            className="bg-transparent border-none outline-none text-white w-full placeholder-slate-600 text-sm font-medium"
                        />
                    </div>

                    {/* Compact Upload Bar */}
                    <div className="relative">
                        <input type="file" id="file-upload" className="hidden" multiple accept=".xlsx, .csv" onChange={handleFileChange} />
                        <label 
                            htmlFor="file-upload" 
                            className="cursor-pointer flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl border border-dashed border-slate-600 hover:border-amber-500 hover:bg-slate-800 transition-all text-slate-400 hover:text-white"
                        >
                            <Plus className="w-4 h-4" />
                            <span className="text-sm font-medium">Add Files</span>
                        </label>
                    </div>
                </div>

                {/* Row 2: File Chips (Horizontal List) */}
                {files.length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-2">
                        {files.map((file, index) => (
                            <div key={index} className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-slate-700 bg-slate-800 text-xs text-slate-300 animate-in zoom-in-95">
                                <FileSpreadsheet className="w-3 h-3 text-amber-500" />
                                <span className="truncate max-w-[150px]">{file.name}</span>
                                <button onClick={() => removeFile(index)} className="hover:text-red-400"><X className="w-3 h-3"/></button>
                            </div>
                        ))}
                        <span className="text-xs text-slate-500 self-center ml-2">{files.length} selected</span>
                    </div>
                )}
            </div>

            {/* RIGHT: Black Rose Button (Compact & Isolated) */}
            <div className="relative flex-shrink-0 self-center">
                 {/* Subtle Glow behind button */}
                 <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-rose-900/20 blur-xl rounded-full pointer-events-none"></div>

                <button 
                    onClick={handleRunAutomation} 
                    disabled={status === 'processing' || files.length === 0}
                    className={`
                        group relative w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300
                        ${status === 'processing' 
                            ? 'bg-slate-900 border border-slate-800 cursor-not-allowed' 
                            : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_20px_rgba(225,29,72,0.4)] hover:scale-105 active:scale-95'
                        }
                    `}
                    title="Run Automation"
                >
                    {status === 'processing' ? (
                        <span className="w-8 h-8 border-2 border-slate-600 border-t-transparent rounded-full animate-spin"></span>
                    ) : (
                        <Flower strokeWidth={1.5} className={`w-8 h-8 text-rose-700 transition-all duration-500 group-hover:text-rose-500 group-hover:rotate-45 group-hover:scale-110`} />
                    )}
                </button>
                
                {status === 'error' && (
                     <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 whitespace-nowrap text-red-400 text-[10px] bg-red-950/90 px-2 py-1 rounded border border-red-900">
                        {message}
                     </div>
                )}
            </div>
        </div>
      </div>

      {/* RESULTS SECTION (More Space!) */}
      {status === 'success' && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 animate-in slide-in-from-bottom-4 duration-700">
          
          {/* Download Card (Small) */}
          <div className={`md:col-span-1 ${THEME.card} border ${THEME.border} p-6 rounded-xl flex flex-col items-center justify-center text-center relative overflow-hidden`}>
             <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-green-500 to-emerald-400"></div>
             <CheckCircle className="w-10 h-10 text-green-400 mb-3" />
             <h3 className="text-lg font-bold text-white mb-1">Done</h3>
             <a href={downloadUrl} className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm font-bold rounded-lg transition-all shadow-lg shadow-green-900/20">
                <Download className="w-4 h-4" /> Download
             </a>
          </div>

          {/* Summary Table (Wide) */}
          <div className={`md:col-span-3 ${THEME.card} border ${THEME.border} p-0 rounded-xl overflow-hidden`}>
             <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/50">
                <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">Financial Summary</h3>
             </div>
             <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-950 text-slate-400 text-xs uppercase">
                    <tr>
                      <th className="p-4 font-semibold">Section</th>
                      <th className="p-4 font-semibold">Type</th>
                      <th className="p-4 text-right font-semibold">TDS Amount</th>
                      <th className="p-4 text-right font-semibold">Interest</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {summaryData.map((row, idx) => (
                      <tr key={idx} className={`transition-colors hover:bg-slate-800/30 ${row.Section === 'Total' ? 'font-bold bg-slate-900 text-amber-400' : 'text-slate-300'}`}>
                        <td className="p-4">{row.Section}</td>
                        <td className="p-4">{row['Co./Non Co.'] || '-'}</td>
                        <td className="p-4 text-right font-mono">₹{row['Total Tax Deducted'].toLocaleString()}</td>
                        <td className="p-4 text-right font-mono">₹{row['Total Interest'].toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
             </div>
          </div>
        </div>
      )}
    </div>
  );
}