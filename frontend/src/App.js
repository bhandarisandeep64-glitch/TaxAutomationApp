import React, { useState } from 'react';
import { MessageSquare, Menu, Send, X, Shield, Flower } from 'lucide-react'; // Added Flower
import { THEME } from './constants/theme';

// --- COMPONENT IMPORTS ---
import Login from './components/Login';
import Sidebar from './components/Sidebar';
import ChatWidget from './components/ChatWidget';
import AdminDashboard from './pages/AdminDashboard';
import ComplianceTable from './pages/ComplianceTable';

// --- MODULES ---
import TdsOdoo from './modules/DirectTax/TdsOdoo';
import TdsZoho from './modules/DirectTax/TdsZoho';
import TdsChallan from './modules/DirectTax/TdsChallan';
import Reco26AS from './modules/DirectTax/Reco26AS';
import FixedAssetRegister from './modules/DirectTax/FixedAssetRegister'; 

import Gstr1Odoo from './modules/IndirectTax/Gstr1Odoo';
import Gstr1Zoho from './modules/IndirectTax/Gstr1Zoho';
import Gstr2bOdoo from './modules/IndirectTax/Gstr2bOdoo';
import Gstr2bZoho from './modules/IndirectTax/Gstr2bZoho';
import RecoGSTR2B from './modules/IndirectTax/RecoGSTR2B'; 
import RecoGSTR2BZoho from './modules/IndirectTax/RecoGSTR2BZoho'; 

export default function App() {
  const [user, setUser] = useState(null);
  const [currentModule, setCurrentModule] = useState('admin_dashboard');
  const [showChat, setShowChat] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [requestedModule, setRequestedModule] = useState('');
  const [requestReason, setRequestReason] = useState('');

  const handleNavigation = (moduleId) => {
    let requiredPermission = '';
    
    if (moduleId.startsWith('tds') || moduleId === '26as_reco' || moduleId === 'fixed_assets') {
        requiredPermission = 'direct_tax';
    }
    if (moduleId.startsWith('gstr')) {
        requiredPermission = 'indirect_tax';
    }

    if (user.role !== 'admin' && requiredPermission && user.restrictedModules && user.restrictedModules.includes(requiredPermission)) {
        setRequestedModule(requiredPermission === 'direct_tax' ? 'Direct Tax' : 'Indirect Tax');
        setShowRequestModal(true);
        return;
    }
    
    setCurrentModule(moduleId);
    setMobileMenuOpen(false);
  };

  const sendAccessRequest = async () => {
      if (!requestReason) return;
      try {
          await fetch('http://127.0.0.1:5000/api/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  username: user.username,
                  content: `Requesting access to ${requestedModule}. Reason: ${requestReason}`,
                  type: 'access_request'
              })
          });
          alert("Request sent to Admin!");
          setShowRequestModal(false);
          setRequestReason('');
      } catch (e) {
          alert("Failed to send.");
      }
  };

  const getPageTitle = (moduleId) => {
    switch(moduleId) {
        case 'admin_dashboard': return 'Overview';
        case 'compliances': return 'Compliance Tracker';
        case 'tds_odoo': return 'TDS Automation | Odoo';
        case 'tds_zoho': return 'TDS Automation | Zoho';
        case 'tds_challan': return 'Challan Payment Mapper';
        case '26as_reco': return '26AS Converter';
        case 'fixed_assets': return 'Depreciation Calculator'; 
        case 'gstr1_odoo': return 'GSTR-1 Automation | Odoo';
        case 'gstr1_zoho': return 'GSTR-1 Processing | Zoho';
        case 'gstr2b_odoo': return 'GSTR-2B Reconciliation | Odoo';
        case 'gstr2b_zoho': return 'GSTR-2B Processing | Zoho';
        case 'gstr3b_odoo': return 'GSTR-3B Reco (Odoo)';
        case 'gstr3b_zoho': return 'GSTR-3B Reco (Zoho)';
        default: return 'Workspace';
    }
  };

  if (!user) {
    return <Login onLogin={(userData) => { 
        setUser(userData); 
        setCurrentModule(userData.role === 'admin' ? 'admin_dashboard' : 'compliances'); 
    }} />;
  }

  const renderContent = () => {
      if (currentModule === 'admin_dashboard') return <AdminDashboard currentUser={user} />;
      if (currentModule === 'compliances') return <ComplianceTable user={user} />; 
      if (currentModule === 'tds_odoo') return <TdsOdoo />;
      if (currentModule === 'tds_zoho') return <TdsZoho />;
      if (currentModule === 'tds_challan') return <TdsChallan />;
      if (currentModule === '26as_reco') return <Reco26AS />;
      if (currentModule === 'fixed_assets') return <FixedAssetRegister />; 
      if (currentModule === 'gstr1_odoo') return <Gstr1Odoo />;
      if (currentModule === 'gstr1_zoho') return <Gstr1Zoho />;
      if (currentModule === 'gstr2b_odoo') return <Gstr2bOdoo />;
      if (currentModule === 'gstr2b_zoho') return <Gstr2bZoho />;
      if (currentModule === 'gstr3b_odoo') return <RecoGSTR2B />; 
      if (currentModule === 'gstr3b_zoho') return <RecoGSTR2BZoho />; 
      
      return (
        <div className="flex flex-col items-center justify-center h-[60vh] text-center">
            <h2 className="text-xl text-white font-bold">Module: {currentModule}</h2>
            <p className="text-zinc-500 mt-2">Under Construction</p>
        </div>
      );
  };

  return (
    <div className={`flex min-h-screen ${THEME.bg} ${THEME.textMain} relative overflow-hidden selection:bg-rose-900 selection:text-white`}>
      
      {/* --- GLOBAL BACKGROUND EFFECTS --- */}
      <div className="fixed inset-0 pointer-events-none z-0">
        {/* Spinning Rose (Subtler than Login) */}
        <div className="absolute top-[60%] -right-[10%] w-[800px] h-[800px] opacity-[0.03] animate-spin-slow">
             <Flower strokeWidth={0.5} className="w-full h-full text-white" />
        </div>
        {/* Dark Gradients */}
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-transparent via-black/50 to-black"></div>
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-rose-900/10 blur-[150px] rounded-full"></div>
      </div>

      {/* Sidebar is Z-10 to sit above background */}
      <div className="relative z-10 flex w-full h-full">
          <Sidebar user={user} onNavigate={handleNavigation} onLogout={() => setUser(null)} currentModule={currentModule} mobileMenuOpen={mobileMenuOpen} />

          <div className="flex-1 md:ml-64 flex flex-col h-screen">
             <header className={`h-16 border-b ${THEME.border} bg-black/20 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-30`}>
                 <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="md:hidden text-zinc-400"><Menu /></button>
                 <h1 className="text-lg font-bold text-zinc-100 hidden md:block tracking-wide uppercase text-sm">{getPageTitle(currentModule)}</h1>
                 <div className="flex items-center gap-4">
                     <button onClick={() => setShowChat(true)} className="relative p-2 text-zinc-400 hover:text-rose-500 transition-colors"><MessageSquare className="w-5 h-5" /></button>
                 </div>
             </header>
             
             {/* Main Content Area */}
             <main className="flex-1 p-6 overflow-y-auto custom-scrollbar">
                {renderContent()}
             </main>
          </div>
      </div>

      {showChat && <ChatWidget user={user} onClose={() => setShowChat(false)} />}

      {showRequestModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
              <div className="bg-zinc-900 border border-rose-900/50 p-6 rounded-xl w-full max-w-md shadow-2xl">
                  <div className="flex justify-between items-start mb-4">
                      <div>
                          <h3 className="text-lg font-bold text-white flex items-center gap-2"><Shield className="w-5 h-5 text-rose-500"/> Access Denied</h3>
                          <p className="text-xs text-zinc-400 mt-1">You do not have permission to view {requestedModule}.</p>
                      </div>
                      <button onClick={() => setShowRequestModal(false)}><X className="w-5 h-5 text-zinc-500 hover:text-white"/></button>
                  </div>
                  <textarea 
                      className="w-full h-24 bg-black border border-zinc-800 rounded-lg p-3 text-sm text-white focus:border-rose-500 outline-none mb-4"
                      placeholder="Reason for access..."
                      value={requestReason}
                      onChange={e => setRequestReason(e.target.value)}
                  />
                  <button onClick={sendAccessRequest} className="w-full py-2 bg-rose-700 hover:bg-rose-600 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2">
                      <Send className="w-4 h-4" /> Send Request to Admin
                  </button>
              </div>
          </div>
      )}

      {/* Global Animation Styles */}
      <style>{`
        @keyframes spin-slow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .animate-spin-slow { animation: spin-slow 120s linear infinite; }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #000; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #444; }
      `}</style>
    </div>
  );
}