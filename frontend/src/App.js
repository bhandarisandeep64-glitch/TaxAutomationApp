import React, { useState } from 'react';
import { MessageSquare, Menu, Send, X, Shield } from 'lucide-react';
import { apiFetch, setToken, getToken } from './api/client';

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
import Gstr3bOdoo from './modules/IndirectTax/Gstr3bOdoo';
import Gstr3bZoho from './modules/IndirectTax/Gstr3bZoho';

export default function App() {
  // Initialize user state from LocalStorage if it exists
const [user, setUser] = useState(() => {
  const savedUser = localStorage.getItem('currentUser');
  // A saved user with no token means a prior session expired -- treat as logged out.
  return savedUser && getToken() ? JSON.parse(savedUser) : null;
});
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
          await apiFetch('/api/chat', {
              method: 'POST',
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
        case 'gstr2b_odoo': return 'GSTR-2B Processing | Odoo';
        case 'gstr2b_zoho': return 'GSTR-2B Processing | Zoho';
        case 'gstr2b_reco_odoo': return 'GSTR-2B Reconciliation | Odoo';
        case 'gstr2b_reco_zoho': return 'GSTR-2B Reconciliation | Zoho';
        case 'gstr3b_odoo': return 'GSTR-3B Working Paper | Odoo';
        case 'gstr3b_zoho': return 'GSTR-3B Working Paper | Zoho';
        default: return 'Workspace';
    }
  };

  if (!user) {
    return <Login onLogin={(userData) => { 
    // SAVE TO STORAGE HERE
    localStorage.setItem('currentUser', JSON.stringify(userData)); 
    
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
      if (currentModule === 'gstr2b_reco_odoo') return <RecoGSTR2B />;
      if (currentModule === 'gstr2b_reco_zoho') return <RecoGSTR2BZoho />;
      if (currentModule === 'gstr3b_odoo') return <Gstr3bOdoo />;
      if (currentModule === 'gstr3b_zoho') return <Gstr3bZoho />;
      
      return (
        <div className="flex flex-col items-center justify-center h-[60vh] text-center">
            <h2 className="text-xl text-neutral-100 font-semibold">Module: {currentModule}</h2>
            <p className="text-neutral-500 mt-2">Coming soon</p>
        </div>
      );
  };

  return (
    <div className="flex min-h-screen bg-neutral-950 text-neutral-100 relative overflow-hidden selection:bg-indigo-500/20 selection:text-indigo-100">

      {/* --- GLOBAL BACKGROUND: flat and precise, no glow --- */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(255,255,255,0.02),_transparent_55%)]" />
      </div>

      {/* Sidebar is Z-10 to sit above background */}
      <div className="relative z-10 flex w-full h-full">
          <Sidebar
    user={user}
    onNavigate={handleNavigation}
    onLogout={() => {
        // CLEAR STORAGE HERE
        localStorage.removeItem('currentUser');
        setToken(null);
        setUser(null);
    }}
    currentModule={currentModule}
    mobileMenuOpen={mobileMenuOpen}
/>

          <div className="flex-1 md:ml-64 flex flex-col h-screen">
             <header className="h-16 border-b border-white/[0.07] bg-neutral-950 flex items-center justify-between px-6 sticky top-0 z-30">
                 <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="md:hidden text-neutral-400"><Menu /></button>
                 <h1 className="text-sm font-semibold text-neutral-200 hidden md:block tracking-wide uppercase">{getPageTitle(currentModule)}</h1>
                 <div className="flex items-center gap-4">
                     <button onClick={() => setShowChat(true)} className="relative p-2 text-neutral-400 hover:text-indigo-400 transition-colors"><MessageSquare className="w-5 h-5" /></button>
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
              <div className="bg-neutral-900 border border-white/[0.08] p-6 rounded-lg w-full max-w-md shadow-lg">
                  <div className="flex justify-between items-start mb-4">
                      <div>
                          <h3 className="text-base font-semibold text-neutral-100 flex items-center gap-2"><Shield className="w-4.5 h-4.5 text-indigo-400"/> Access Denied</h3>
                          <p className="text-xs text-neutral-500 mt-1">You do not have permission to view {requestedModule}.</p>
                      </div>
                      <button onClick={() => setShowRequestModal(false)}><X className="w-5 h-5 text-neutral-500 hover:text-neutral-200"/></button>
                  </div>
                  <textarea
                      className="w-full h-24 bg-black/30 border border-white/[0.08] rounded-md p-3 text-sm text-neutral-100 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors mb-4"
                      placeholder="Reason for access..."
                      value={requestReason}
                      onChange={e => setRequestReason(e.target.value)}
                  />
                  <button onClick={sendAccessRequest} className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm rounded-md transition-colors flex items-center justify-center gap-2">
                      <Send className="w-4 h-4" /> Send Request to Admin
                  </button>
              </div>
          </div>
      )}

      {/* Global Animation Styles */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #2a2a2e; border-radius: 3px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #3a3a3e; }
      `}</style>
    </div>
  );
}