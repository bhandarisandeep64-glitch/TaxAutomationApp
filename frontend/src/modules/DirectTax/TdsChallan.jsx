import React, { useState } from 'react';
import { 
  Upload, CreditCard, CheckCircle, AlertCircle, Download, Flower, Calendar, FileSpreadsheet, X, Plus, Type
} from 'lucide-react';
import { THEME } from '../../constants/theme';

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

  // --- HANDLERS ---

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
      const res = await fetch('https://taxautomationapp.onrender.com/api/direct-tax/challan/analyze', {
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
      const res = await fetch('https://taxautomationapp.onrender.com/api/direct-tax/challan/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: filePath,
          inputs: inputs,
          custom_name: reportName
        })
      });
      const data = await res.json();

      if (res.ok) {
        setDownloadUrl(`https://taxautomationapp.onrender.com${data.download_url}`);
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
      
      {/* HEADER */}
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
        <CreditCard className={`w-6 h-6 ${THEME.accent}`} />
        <h2 className="text-xl font-bold text-white tracking-tight">Challan Payment Mapper</h2>
      </div>

      {/* STEP 1: COMPACT UPLOAD & ANALYZE */}
      {step === 1 && (
        <div className={`p-6 rounded-2xl border ${THEME.border} bg-slate-900/50 shadow-xl`}>
            <div className="flex flex-col md:flex-row gap-8 items-center">
                
                {/* LEFT: File Input */}
                <div className="flex-1 w-full space-y-4">
                    <div className="relative">
                        <input type="file" id="challan-upload" className="hidden" accept=".xlsx, .csv" onChange={handleFileChange} />
                        <label 
                            htmlFor="challan-upload" 
                            className="cursor-pointer flex items-center justify-center gap-2 w-full px-4 py-4 rounded-xl border border-dashed border-slate-600 hover:border-amber-500 hover:bg-slate-800 transition-all text-slate-400 hover:text-white"
                        >
                            <Plus className="w-5 h-5" />
                            <span className="text-sm font-medium">Select TDS File to Analyze</span>
                        </label>
                    </div>

                    {/* File Chip */}
                    {file && (
                        <div className="flex items-center gap-3 p-3 rounded-lg border border-slate-700 bg-slate-800 text-sm text-slate-300 animate-in zoom-in-95">
                            <div className="p-2 bg-slate-700 rounded">
                                <FileSpreadsheet className="w-4 h-4 text-amber-500" />
                            </div>
                            <span className="truncate flex-1">{file.name}</span>
                            <button onClick={removeFile} className="p-1 hover:bg-red-900/30 hover:text-red-400 rounded transition-colors">
                                <X className="w-4 h-4"/>
                            </button>
                        </div>
                    )}
                </div>

                {/* RIGHT: Black Rose Button (Analyze) */}
                <div className="relative flex-shrink-0">
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-rose-900/20 blur-xl rounded-full pointer-events-none"></div>
                    <button 
                        onClick={handleAnalyze} 
                        disabled={status === 'processing' || !file}
                        className={`
                            group relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-500
                            ${status === 'processing' 
                                ? 'bg-slate-900 border border-slate-800 cursor-not-allowed' 
                                : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_30px_rgba(225,29,72,0.4)] hover:scale-105 active:scale-95'
                            }
                        `}
                        title="Analyze File"
                    >
                        {status === 'processing' ? (
                            <span className="w-10 h-10 border-2 border-slate-600 border-t-transparent rounded-full animate-spin"></span>
                        ) : (
                            <Flower strokeWidth={1.5} className={`w-10 h-10 text-rose-700 transition-all duration-500 group-hover:text-rose-500 group-hover:rotate-45 group-hover:scale-110`} />
                        )}
                    </button>
                    
                    {status === 'error' && (
                        <div className="absolute top-full left-1/2 -translate-x-1/2 mt-4 whitespace-nowrap text-red-400 text-xs bg-red-950/90 px-3 py-1.5 rounded border border-red-900">
                            {message}
                        </div>
                    )}
                </div>
            </div>
        </div>
      )}

      {/* STEP 2: MANUAL ENTRY (Cards) */}
      {step === 2 && (
        <div className="space-y-8 animate-in slide-in-from-right-8 duration-500">
           
           {/* Top Bar: Name Input */}
           <div className="flex justify-end items-center gap-4">
              <div className="flex items-center gap-3 px-4 py-2 rounded-xl border border-slate-700 bg-slate-900 focus-within:border-amber-500 transition-colors w-full max-w-xs">
                  <Type className="w-4 h-4 text-slate-500" />
                  <input 
                      type="text" 
                      placeholder="Custom Name (Optional)" 
                      value={reportName}
                      onChange={(e) => setReportName(e.target.value)}
                      className="bg-transparent border-none outline-none text-white w-full placeholder-slate-600 text-sm"
                  />
              </div>
           </div>

           {/* THE CARDS */}
           <div className="space-y-6">
              {groups.map((grp, idx) => {
                 const key = `${grp.Section}|${grp['Co./Non Co.']}`;
                 return (
                    <div key={idx} className={`rounded-xl border border-slate-700 bg-slate-900 overflow-hidden shadow-lg hover:border-slate-600 transition-colors`}>
                       
                       {/* Card Header */}
                       <div className="px-6 py-4 bg-slate-800/50 border-b border-slate-700 flex justify-between items-center">
                          <div className="flex items-center gap-3">
                              <span className="text-lg font-bold text-white">{grp.Section}</span>
                              <span className="text-slate-600">•</span>
                              <span className="text-sm font-medium text-slate-400 uppercase">{grp['Co./Non Co.']}</span>
                          </div>
                          <div className="bg-red-950/30 border border-red-900/30 text-red-400 px-3 py-1 rounded text-xs font-bold uppercase tracking-wider">
                             Due: ₹{grp.Total_Tax_Pending.toLocaleString()}
                          </div>
                       </div>

                       {/* Inputs Grid */}
                       <div className="p-6 grid grid-cols-1 md:grid-cols-6 gap-4">
                          
                          <div className="md:col-span-1 space-y-1">
                             <label className="text-[10px] font-bold text-slate-500 uppercase">Challan No</label>
                             <input type="text" className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:border-amber-500 outline-none transition-colors" 
                                onChange={(e) => handleInputChange(key, 'challan_no', e.target.value)}
                             />
                          </div>

                          <div className="md:col-span-1 space-y-1">
                             <label className="text-[10px] font-bold text-slate-500 uppercase">Date</label>
                             <div className="relative">
                                <input type="date" className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:border-amber-500 outline-none transition-colors appearance-none" 
                                   onChange={(e) => handleInputChange(key, 'date', e.target.value)}
                                />
                                <Calendar className="w-3.5 h-3.5 text-slate-500 absolute right-3 top-3 pointer-events-none" />
                             </div>
                          </div>

                          <div className="md:col-span-1 space-y-1">
                             <label className="text-[10px] font-bold text-slate-500 uppercase">BSR Code</label>
                             <input type="text" className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:border-amber-500 outline-none transition-colors" 
                                onChange={(e) => handleInputChange(key, 'bsr', e.target.value)}
                             />
                          </div>

                          <div className="md:col-span-1 space-y-1">
                             <label className="text-[10px] font-bold text-slate-500 uppercase">Amount</label>
                             <input type="number" className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:border-amber-500 outline-none transition-colors" 
                                onChange={(e) => handleInputChange(key, 'amount', e.target.value)}
                             />
                          </div>

                          <div className="md:col-span-1 space-y-1">
                             <label className="text-[10px] font-bold text-slate-500 uppercase">Interest</label>
                             <input type="number" className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:border-amber-500 outline-none transition-colors" 
                                onChange={(e) => handleInputChange(key, 'interest', e.target.value)}
                             />
                          </div>

                          <div className="md:col-span-1 space-y-1">
                             <label className="text-[10px] font-bold text-slate-500 uppercase">Total</label>
                             <input type="number" className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:border-amber-500 outline-none transition-colors" 
                                onChange={(e) => handleInputChange(key, 'total', e.target.value)}
                             />
                          </div>

                       </div>
                    </div>
                 );
              })}
           </div>

           {/* FLOATING ACTION BUTTON (Black Rose for Update) */}
           <div className="flex justify-end pt-4 pb-10">
              <div className="relative group">
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-rose-900/20 blur-xl rounded-full pointer-events-none"></div>
                  <button 
                     onClick={handleUpdate}
                     disabled={status === 'processing'}
                     className={`
                        relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300
                        ${status === 'processing' 
                            ? 'bg-slate-900 border border-slate-800 cursor-not-allowed' 
                            : 'bg-black border border-rose-900/50 shadow-[0_0_0_1px_rgba(225,29,72,0.2)] hover:shadow-[0_0_30px_rgba(225,29,72,0.4)] hover:scale-105 active:scale-95'
                        }
                     `}
                     title="Update & Download"
                  >
                     {status === 'processing' ? (
                        <span className="w-10 h-10 border-2 border-slate-600 border-t-transparent rounded-full animate-spin"></span>
                     ) : (
                        <Flower strokeWidth={1.5} className={`w-10 h-10 text-rose-700 transition-all duration-500 group-hover:text-rose-500 group-hover:rotate-45 group-hover:scale-110`} />
                     )}
                  </button>
              </div>
           </div>
        </div>
      )}

      {/* STEP 3: SUCCESS */}
      {step === 3 && (
         <div className={`p-12 rounded-2xl border border-green-900/30 bg-green-900/10 text-center animate-in zoom-in-95`}>
            <div className="w-20 h-20 bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-10 h-10 text-green-500" />
            </div>
            <h2 className="text-3xl font-bold text-white mb-2">Challans Mapped Successfully!</h2>
            <p className="text-slate-400 mb-8">Your file has been updated with the details provided.</p>
            <a href={downloadUrl} className="inline-flex items-center gap-2 px-8 py-4 bg-green-600 hover:bg-green-500 text-white font-bold rounded-xl transition-colors shadow-lg">
               <Download className="w-5 h-5" /> Download Updated File
            </a>
            <button onClick={() => {setStep(1); setFile(null);}} className="block mt-6 mx-auto text-slate-500 hover:text-white text-sm underline">
                Process Another File
            </button>
         </div>
      )}
    </div>
  );
}