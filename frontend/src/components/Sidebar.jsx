import React, { useState } from 'react';
import { FileText, CheckCircle, Users, LogOut, ChevronDown, ChevronRight, Lock, Landmark, Flower } from 'lucide-react'; 
import { THEME } from '../constants/theme';

export default function Sidebar({ user, onNavigate, onLogout, currentModule, mobileMenuOpen }) {
  const [expandedMenus, setExpandedMenus] = useState({});

  // Helper to check if a module is allowed
  const isAllowed = (moduleId) => {
    if (user.role === 'admin') return true;
    if (moduleId === 'compliances') return true;
    
    // Check if the module ID is in the restricted list
    if (user.restrictedModules && user.restrictedModules.includes(moduleId)) {
      return false;
    }
    return true;
  };

  const menuStructure = [
    { 
      title: "Compliances", 
      id: "compliances", 
      icon: CheckCircle 
    },
    {
      title: "Direct Tax",
      id: "direct_tax",
      icon: FileText,
      sub: [
        { title: "TDS", id: "tds", sub: [{ title: "Odoo", id: "tds_odoo" }, { title: "Zoho", id: "tds_zoho" }, { title: "Challan Mapper", id: "tds_challan" }] },
        { title: "26AS Reco", id: "26as_reco" },
        { title: "TDS Returns", id: "tds_returns", sub: [{ title: "26Q", id: "ret_26q" }, { title: "24Q", id: "ret_24q" }, { title: "27Q", id: "ret_27q" }] },
        { title: "Depreciation Calculator", id: "fixed_assets", icon: Landmark }
      ]
    },
    {
      title: "Indirect Tax",
      id: "indirect_tax",
      icon: FileText,
      sub: [
        { title: "GSTR 1", id: "gstr1", sub: [{ title: "Odoo", id: "gstr1_odoo" }, { title: "Zoho", id: "gstr1_zoho" }] },
        { title: "GSTR 2B", id: "gstr2b", sub: [{ title: "Odoo", id: "gstr2b_odoo" }, { title: "Zoho", id: "gstr2b_zoho" }] },
        { title: "GSTR 3B", id: "gstr3b", sub: [
            { title: "Odoo", id: "gstr3b_odoo" },
            { title: "Zoho", id: "gstr3b_zoho" }
        ] }
      ]
    }
  ];

  const toggleMenu = (key) => setExpandedMenus(prev => ({...prev, [key]: !prev[key]}));

  // Helper for safe Tailwind padding
  const getPaddingClass = (depth) => {
    if (depth === 0) return '';
    if (depth === 1) return 'pl-8';
    if (depth === 2) return 'pl-12';
    return 'pl-16';
  };

  const renderMenu = (items, depth = 0) => {
    return items.map((item) => {
      const allowed = isAllowed(item.id);
      
      return (
        <div key={item.id} className="w-full">
          <button
            onClick={() => {
              if (!allowed) return; 

              if (item.sub) toggleMenu(item.id);
              else onNavigate(item.id);
            }}
            className={`
              w-full flex items-center justify-between p-3 
              ${getPaddingClass(depth)} 
              ${!allowed ? 'cursor-not-allowed opacity-40' : 'hover:bg-slate-800 cursor-pointer'} 
              transition-colors text-sm group relative
              ${currentModule === item.id ? 'bg-slate-800 text-amber-400 border-l-2 border-amber-500' : ''}
            `}
          >
            <div className="flex items-center gap-3">
              {(depth === 0 || item.icon) && (
                 item.icon ? <item.icon className={`w-4 h-4 ${depth === 0 ? THEME.accent : 'text-slate-500'}`} /> : null
              )}
              <span className={depth === 0 ? "font-semibold text-slate-200" : "text-slate-400"}>
                {item.title}
              </span>
            </div>
            
            <div className="flex items-center gap-2">
              {!allowed && <Lock className="w-3 h-3 text-red-500" />}
              
              {item.sub && (
                expandedMenus[item.id] 
                  ? <ChevronDown className="w-4 h-4 text-slate-500"/> 
                  : <ChevronRight className="w-4 h-4 text-slate-500"/>
              )}
            </div>
          </button>
          
          {item.sub && expandedMenus[item.id] && allowed && (
            <div className="bg-slate-950/30 border-l border-slate-800 ml-4">
              {renderMenu(item.sub, depth + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <aside className={`fixed inset-y-0 left-0 z-40 w-64 transform ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 transition-transform duration-300 ease-in-out ${THEME.sidebar} border-r ${THEME.border}`}>
        
        {/* --- BRANDING HEADER --- */}
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-black border border-rose-900/50 flex items-center justify-center shadow-[0_0_10px_rgba(225,29,72,0.2)]">
                <Flower className={`w-5 h-5 ${THEME.accent}`} strokeWidth={1.5} />
            </div>
            <span className="font-bold text-lg tracking-wide text-slate-100 uppercase">
                BLACK ROSE <span className={THEME.accent}>INC.</span>
            </span>
        </div>

        <nav className="p-4 space-y-1 h-[calc(100vh-140px)] overflow-y-auto custom-scrollbar">
            {user.role === 'admin' && (
               <button 
                 onClick={() => onNavigate('admin_dashboard')} 
                 className={`w-full flex items-center gap-3 p-3 rounded mb-4 transition-colors ${currentModule === 'admin_dashboard' ? 'bg-amber-600 text-slate-900 font-bold' : 'text-slate-300 hover:bg-slate-800'}`}
               >
                  <Users className="w-4 h-4" /> Admin Dashboard
               </button>
            )}
            
            <div className="pb-4 mb-4 border-b border-slate-800">
               <p className="px-3 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Modules</p>
               {renderMenu(menuStructure)}
            </div>
        </nav>

        <div className="absolute bottom-0 w-full p-4 border-t border-slate-800 bg-slate-900">
             <div className="flex items-center gap-3 mb-3">
                 <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center font-bold text-xs text-white">
                    {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
                 </div>
                 <div className="overflow-hidden">
                    <p className="text-sm font-medium truncate text-white">{user.name}</p>
                    <p className="text-xs text-slate-500 capitalize">{user.role}</p>
                 </div>
             </div>
             <button onClick={onLogout} className="w-full flex items-center justify-center gap-2 text-xs text-red-400 hover:text-red-300 transition-colors">
                <LogOut className="w-3 h-3" /> Sign Out
             </button>
        </div>
    </aside>
  );
}