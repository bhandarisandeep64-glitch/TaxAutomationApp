import React, { useState } from 'react';
import { 
  Upload, FileSpreadsheet, CheckCircle, AlertCircle, Download, Type, Flower, X 
} from 'lucide-react';
import { THEME } from '../../constants/theme';

// Uncomment next line in your local environment
// import blackRose from '../../assets/black-rose.png'; 

export default function Gstr1Zoho() {
  // The exact keys expected by Python
  const [files, setFiles] = useState({
    file_invoice_details: null,
    file_credit_note_details: null,
    file_invoice_credit_notes: null,
    file_export_invoices: null
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
    // Must have at least one header file
    if (!files.file_invoice_credit_notes && !files.file_export_invoices) {
        setMessage("Please upload at least one Header file (Slot 3 or 4).");
        setStatus('error');
        return;
    }

    setStatus('processing');
    const formData = new FormData();
    
    // Append files with correct keys
    Object.keys(files).forEach(key => {
      if (files[key]) formData.append(key, files[key]);
    });
    
    formData.append('custom_name', reportName);

    try {
      const response = await fetch('https://taxautomationapp.onrender.com/api/indirect-tax/gstr1-zoho', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (response.ok) {
        setStatus('success');
        setMessage(data.message);
        setDownloadUrl(`https://taxautomationapp.onrender.com${data.download_url}`);
        setFinalFileName(data.filename || 'GSTR1_Zoho_Processed.xlsx');
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

  const UploadSlot = ({ title, slotKey, color }) => (
    <div className={`relative border-2 border-dashed ${files[slotKey] ? 'border-green-500/50 bg-green-900/10' : 'border-slate-700 bg-slate-900/30'} rounded-xl p-4 flex flex-col justify-center items-center text-center h-32 transition-all hover:border-${color}-500/50 group`}>
        <input type="file" id={`upload-${slotKey}`} className="hidden" accept=".xlsx, .csv" onChange={handleFileChange(slotKey)} />
        
        {files[slotKey] ? (
            <div className="w-full relative">
                <button onClick={() => removeFile(slotKey)} className="absolute -top-2 -right-2 text-slate-500 hover:text-red-400"><X className="w-4 h-4"/></button>
                <FileSpreadsheet className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-xs text-green-400 font-medium truncate px-2">{files[slotKey].name}</p>
            </div>
        ) : (
            <label htmlFor={`upload-${slotKey}`} className="cursor-pointer w-full h-full flex flex-col items-center justify-center">
                <Upload className={`w-6 h-6 text-slate-500 group-hover:text-${color}-400 mb-2`} />
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wide">{title}</span>
                <span className="text-[10px] text-slate-500 mt-1">Click to Add</span>
            </label>
        )}
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500 pt-4">
      
      <div className={`p-6 rounded-2xl border ${THEME.border} bg-slate-900/50 shadow-xl`}>
        {/* Name Input */}
        <div className="mb-6 max-w-md">
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-slate-700 bg-slate-950 focus-within:border-amber-500 transition-colors">
                <Type className="w-4 h-4 text-slate-500" />
                <input type="text" placeholder="Report Name (e.g. Nov 2025 Sales)" value={reportName} onChange={(e) => setReportName(e.target.value)}
                    className="bg-transparent border-none outline-none text-white w-full placeholder-slate-600 text-sm font-medium" />
            </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 items-center">
            {/* 4 Slots */}
            <div className="flex-1 w-full grid grid-cols-2 gap-4">
                <UploadSlot title="1. Invoice Details" slotKey="file_invoice_details" color="blue" />
                <UploadSlot title="2. Credit Note Details" slotKey="file_credit_note_details" color="indigo" />
                <UploadSlot title="3. Inv/CN Headers" slotKey="file_invoice_credit_notes" color="purple" />
                <UploadSlot title="4. Export Invoices" slotKey="file_export_invoices" color="pink" />
            </div>

            {/* Black Rose Button */}
            <div className="relative flex-shrink-0 self-center pl-4">
                 <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 blur-2xl rounded-full pointer-events-none transition-all duration-500 ${status === 'processing' ? 'bg-rose-600/40' : 'bg-rose-900/20'}`}></div>
                <button onClick={handleRunAutomation} disabled={status === 'processing'}
                    className={`group relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 ${status === 'processing' ? 'bg-slate-950 border-2 border-rose-900 cursor-not-allowed' : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_20px_rgba(225,29,72,0.4)] hover:scale-105 active:scale-95'}`}
                    title="Process Files"
                >
                    {status === 'processing' ? (
                        <div className="relative flex items-center justify-center">
                            <span className="absolute inset-0 rounded-full border-2 border-t-rose-500 border-r-rose-500 border-b-transparent border-l-transparent animate-spin"></span>
                            <Flower strokeWidth={1.5} className="w-10 h-10 text-rose-600 animate-spin-slow" />
                        </div>
                    ) : (
                        <Flower strokeWidth={1} className="w-12 h-12 text-rose-800 transition-all duration-700 group-hover:text-rose-600 group-hover:rotate-180 group-hover:scale-110 animate-pulse-slow opacity-90 group-hover:opacity-100" />
                    )}
                </button>
                {status === 'error' && <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 whitespace-nowrap text-red-400 text-[10px] bg-red-950/90 px-2 py-1 rounded border border-red-900">{message}</div>}
            </div>
        </div>
      </div>

      {/* Results */}
      {status === 'success' && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 animate-in slide-in-from-bottom-4 duration-700">
          <div className={`md:col-span-1 ${THEME.card} border ${THEME.border} p-6 rounded-xl flex flex-col items-center justify-center text-center relative overflow-hidden`}>
             <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-indigo-400"></div>
             <CheckCircle className="w-10 h-10 text-purple-400 mb-3" />
             <h3 className="text-lg font-bold text-white mb-1">Ready</h3>
             <a href={downloadUrl} download={finalFileName} className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-sm font-bold rounded-lg transition-all shadow-lg shadow-purple-900/20">
                <Download className="w-4 h-4" /> Download Excel
             </a>
          </div>
          <div className={`md:col-span-3 ${THEME.card} border ${THEME.border} p-0 rounded-xl overflow-hidden`}>
             <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/50"><h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">Sales Summary</h3></div>
             <div className="overflow-x-auto">
                <table className="w-full text-left text-sm"><thead className="bg-slate-950 text-slate-400 text-xs uppercase"><tr><th className="p-4 font-semibold">Category</th><th className="p-4 text-right font-semibold">Total Taxable</th><th className="p-4 text-right font-semibold">IGST</th><th className="p-4 text-right font-semibold">CGST</th><th className="p-4 text-right font-semibold">SGST</th></tr></thead>
                  <tbody className="divide-y divide-slate-800">{summaryData.map((row, idx) => (
                      <tr key={idx} className={`transition-colors hover:bg-slate-800/30`}><td className="p-4">{row.Category}</td><td className="p-4 text-right font-mono">₹{row.Taxable?.toLocaleString()}</td><td className="p-4 text-right font-mono">₹{row.IGST?.toLocaleString()}</td><td className="p-4 text-right font-mono">₹{row.CGST?.toLocaleString()}</td><td className="p-4 text-right font-mono">₹{row.SGST?.toLocaleString()}</td></tr>
                    ))}</tbody></table>
             </div>
          </div>
        </div>
      )}
    </div>
  );
}