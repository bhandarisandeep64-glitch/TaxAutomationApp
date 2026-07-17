import React, { useState } from 'react';
import { FileText, CheckCircle, Users, LogOut, ChevronDown, ChevronRight, Lock, Landmark, Flower, TrendingUp } from 'lucide-react';

export default function Sidebar({ user, onNavigate, onLogout, currentModule, mobileMenuOpen }) {
  const [expandedMenus, setExpandedMenus] = useState({});

  const isAllowed = (moduleId) => {
    if (user.role === 'admin') return true;
    if (moduleId === 'compliances') return true;
    if (user.restrictedModules && user.restrictedModules.includes(moduleId)) {
      return false;
    }
    return true;
  };

  const menuStructure = [
    { title: "Compliances", id: "compliances", icon: CheckCircle },
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
        { title: "GSTR 3B", id: "gstr3b", sub: [{ title: "Odoo", id: "gstr3b_odoo" }, { title: "Zoho", id: "gstr3b_zoho" }] }
      ]
    },
    {
      title: "Mario",
      id: "mario",
      icon: TrendingUp,
      sub: [
        { title: "Sales", id: "mario_sales" },
        { title: "Purchase", id: "mario_purchase" }
      ]
    }
  ];

  const toggleMenu = (key) => setExpandedMenus(prev => ({ ...prev, [key]: !prev[key] }));

  const getPaddingClass = (depth) => {
    if (depth === 0) return '';
    if (depth === 1) return 'pl-8';
    if (depth === 2) return 'pl-12';
    return 'pl-16';
  };

  const renderMenu = (items, depth = 0) => {
    return items.map((item) => {
      const allowed = isAllowed(item.id);
      const active = currentModule === item.id;

      return (
        <div key={item.id} className="w-full">
          <button
            onClick={() => {
              if (!allowed) return;
              if (item.sub) toggleMenu(item.id);
              else onNavigate(item.id);
            }}
            className={`
              w-full flex items-center justify-between p-2.5 rounded-lg
              ${getPaddingClass(depth)}
              ${!allowed ? 'cursor-not-allowed opacity-40' : 'hover:bg-white/[0.04] cursor-pointer'}
              transition-colors text-sm group relative
              ${active ? 'bg-amber-500/10 text-amber-400' : ''}
            `}
          >
            <div className="flex items-center gap-3">
              {(depth === 0 || item.icon) && (
                item.icon ? <item.icon className={`w-4 h-4 ${depth === 0 ? (active ? 'text-amber-400' : 'text-neutral-500') : 'text-neutral-600'}`} /> : null
              )}
              <span className={depth === 0 ? `font-medium ${active ? 'text-amber-400' : 'text-neutral-200'}` : 'text-neutral-400'}>
                {item.title}
              </span>
            </div>

            <div className="flex items-center gap-2">
              {!allowed && <Lock className="w-3 h-3 text-red-500/70" />}
              {item.sub && (
                expandedMenus[item.id]
                  ? <ChevronDown className="w-4 h-4 text-neutral-600" />
                  : <ChevronRight className="w-4 h-4 text-neutral-600" />
              )}
            </div>
          </button>

          {item.sub && expandedMenus[item.id] && allowed && (
            <div className="border-l border-white/[0.06] ml-4 mt-0.5 mb-1">
              {renderMenu(item.sub, depth + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <aside className={`fixed inset-y-0 left-0 z-40 w-64 transform ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 transition-transform duration-300 ease-in-out bg-neutral-950/95 border-r border-white/[0.06] backdrop-blur-xl flex flex-col`}>

      {/* Brand */}
      <div className="p-5 border-b border-white/[0.06] flex items-center gap-3 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-neutral-900 border border-rose-900/40 flex items-center justify-center">
          <Flower className="w-4 h-4 text-rose-700" strokeWidth={1.5} />
        </div>
        <span className="font-semibold text-sm tracking-[0.1em] text-neutral-100 uppercase">
          Black Rose <span className="text-amber-400">Inc.</span>
        </span>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto custom-scrollbar">
        {user.role === 'admin' && (
          <button
            onClick={() => onNavigate('admin_dashboard')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-3 transition-colors text-sm font-medium ${currentModule === 'admin_dashboard' ? 'bg-amber-500 text-neutral-950' : 'text-neutral-300 hover:bg-white/[0.04]'}`}
          >
            <Users className="w-4 h-4" /> Admin Dashboard
          </button>
        )}

        <div className="pb-3 mb-3 border-b border-white/[0.06]">
          <p className="px-2.5 text-[11px] font-semibold text-neutral-600 uppercase tracking-[0.12em] mb-2">Modules</p>
          {renderMenu(menuStructure)}
        </div>
      </nav>

      <div className="p-4 border-t border-white/[0.06] bg-neutral-950 shrink-0">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-neutral-800 border border-white/[0.06] flex items-center justify-center font-semibold text-xs text-neutral-200">
            {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div className="overflow-hidden">
            <p className="text-sm font-medium truncate text-neutral-100">{user.name}</p>
            <p className="text-xs text-neutral-500 capitalize">{user.role}</p>
          </div>
        </div>
        <button onClick={onLogout} className="w-full flex items-center justify-center gap-2 py-1.5 rounded-lg text-xs text-neutral-500 hover:text-red-400 hover:bg-red-500/5 transition-colors">
          <LogOut className="w-3.5 h-3.5" /> Sign Out
        </button>
      </div>
    </aside>
  );
}
