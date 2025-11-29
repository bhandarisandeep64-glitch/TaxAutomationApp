import React, { useState } from 'react';
import { 
  Upload, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  Download, 
  Type, 
  Flower, 
  X, 
  FileJson
} from 'lucide-react';
import { THEME } from '../../constants/theme';

// --- LOCAL SETUP ---
// Uncomment this line in your VS Code to use the real image
// import blackRose from '../../assets/black-rose.png'; 

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
    // Only sending the Portal File
    formData.append('portal_file', file);
    formData.append('custom_name', reportName);

    try {
      const response = await fetch('http://127.0.0.1:5000/api/direct-tax/26as-reco', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (response.ok) {
        setStatus('success');
        setMessage(data.message);
        setDownloadUrl(`http://127.0.0.1:5000${data.download_url}`);
        setFinalFileName(data.filename || '26AS_Converted.xlsx');
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
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-500 pt-4">
      
      {/* HEADER */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
        <FileJson className={`w-6 h-6 ${THEME.accent}`} />
        <h2 className="text-xl font-bold text-white tracking-tight">26AS Converter <span className="text-slate-600">|</span> TRACES</h2>
      </div>

      {/* COMPACT CONTROL PANEL */}
      <div className={`p-6 rounded-2xl border ${THEME.border} bg-slate-900/50 shadow-xl`}>
        <div className="flex flex-col md:flex-row gap-8 items-center">
            
            {/* LEFT: Inputs */}
            <div className="flex-1 w-full space-y-4">
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Name Input */}
                    <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-slate-700 bg-slate-950 focus-within:border-amber-500 transition-colors">
                        <Type className="w-4 h-4 text-slate-500" />
                        <input 
                            type="text" 
                            placeholder="Report Name (e.g. FY 24-25 Q3)" 
                            value={reportName}
                            onChange={(e) => setReportName(e.target.value)}
                            className="bg-transparent border-none outline-none text-white w-full placeholder-slate-600 text-sm font-medium"
                        />
                    </div>

                    {/* Upload Bar (Single File) */}
                    <div className="relative">
                        <input type="file" id="26as-upload" className="hidden" accept=".txt, .html" onChange={handleFileChange} />
                        <label 
                            htmlFor="26as-upload" 
                            className="cursor-pointer flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl border border-dashed border-slate-600 hover:border-amber-500 hover:bg-slate-800 transition-all text-slate-400 hover:text-white"
                        >
                            <Upload className="w-4 h-4" />
                            <span className="text-sm font-medium">Upload 26AS File</span>
                        </label>
                    </div>
                </div>

                {/* File Chip */}
                {file && (
                    <div className="flex items-center gap-3 p-3 rounded-lg border border-slate-700 bg-slate-800 text-sm text-slate-300 animate-in zoom-in-95 w-full md:w-1/2">
                        <div className="p-2 bg-slate-700 rounded">
                            <FileText className="w-4 h-4 text-amber-500" />
                        </div>
                        <span className="truncate flex-1">{file.name}</span>
                        <button onClick={removeFile} className="p-1 hover:bg-red-900/30 hover:text-red-400 rounded transition-colors">
                            <X className="w-4 h-4"/>
                        </button>
                    </div>
                )}
            </div>

            {/* RIGHT: THE ANIMATED BLACK ROSE BUTTON */}
            <div className="relative flex-shrink-0 self-center pl-4">
                 <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 blur-2xl rounded-full pointer-events-none transition-all duration-500 ${status === 'processing' ? 'bg-rose-600/40' : 'bg-rose-900/20'}`}></div>

                <button 
                    onClick={handleRunAutomation} 
                    disabled={status === 'processing' || !file}
                    className={`
                        group relative w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300
                        ${status === 'processing' 
                            ? 'bg-slate-950 border-2 border-rose-900 cursor-not-allowed' 
                            : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_20px_rgba(225,29,72,0.4)] hover:scale-105 active:scale-95'
                        }
                    `}
                    title="Convert 26AS"
                >
                    {status === 'processing' ? (
                        <div className="relative flex items-center justify-center">
                            <span className="absolute inset-0 rounded-full border-2 border-t-rose-500 border-r-rose-500 border-b-transparent border-l-transparent animate-spin"></span>
                            {/* LOCALLY USE: <img src={blackRose} ... /> */}
                            <Flower strokeWidth={1.5} className="w-10 h-10 text-rose-600 animate-spin-slow" />
                        </div>
                    ) : (
                        // LOCALLY USE: <img src={blackRose} ... />
                        <Flower 
                            strokeWidth={1} 
                            className="w-12 h-12 text-rose-800 transition-all duration-700 group-hover:text-rose-600 group-hover:rotate-180 group-hover:scale-110 animate-pulse-slow opacity-90 group-hover:opacity-100"
                        />
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

      {/* RESULTS SECTION */}
      {status === 'success' && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 animate-in slide-in-from-bottom-4 duration-700">
          
          {/* Download Card */}
          <div className={`md:col-span-1 ${THEME.card} border ${THEME.border} p-6 rounded-xl flex flex-col items-center justify-center text-center relative overflow-hidden`}>
             <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-500 to-orange-400"></div>
             <CheckCircle className="w-10 h-10 text-amber-400 mb-3" />
             <h3 className="text-lg font-bold text-white mb-1">Converted</h3>
             <a 
                href={downloadUrl} 
                download={finalFileName}
                className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-sm font-bold rounded-lg transition-all shadow-lg shadow-amber-900/20"
             >
                <Download className="w-4 h-4" /> Download Excel
             </a>
          </div>

          {/* Summary Table */}
          <div className={`md:col-span-3 ${THEME.card} border ${THEME.border} p-0 rounded-xl overflow-hidden`}>
             <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/50">
                <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">26AS Summary</h3>
             </div>
             <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-950 text-slate-400 text-xs uppercase">
                    <tr>
                      <th className="p-4 font-semibold">Description</th>
                      <th className="p-4 text-right font-semibold">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {summaryData.map((row, idx) => (
                      <tr key={idx} className="transition-colors hover:bg-slate-800/30">
                        <td className="p-4 text-slate-300">{row.Category}</td>
                        <td className="p-4 text-right font-mono font-bold text-amber-400">₹{row.Amount?.toLocaleString()}</td>
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