import React from 'react';
import { Loader2, X, Upload as UploadIcon, FileSpreadsheet } from 'lucide-react';
import { THEME } from '../../constants/theme';

// Shared visual primitives so every screen in the app reads as one
// consistent, corporate-premium product instead of 18 independently
// styled pages. Pure presentation -- no data fetching or business logic.

export function PageHeader({ icon: Icon, title, eyebrow, subtitle, action }) {
  return (
    <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 border-b border-white/[0.06] pb-6">
      <div className="flex items-center gap-4">
        {Icon && (
          <div className="w-11 h-11 rounded-xl bg-neutral-900 border border-white/[0.06] flex items-center justify-center shrink-0">
            <Icon className="w-5 h-5 text-amber-400" strokeWidth={1.75} />
          </div>
        )}
        <div>
          {eyebrow && (
            <p className="text-[11px] font-semibold text-neutral-500 uppercase tracking-[0.15em] mb-0.5">{eyebrow}</p>
          )}
          <h1 className="text-2xl font-semibold text-neutral-50 tracking-tight">{title}</h1>
          {subtitle && <p className="text-sm text-neutral-500 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function Card({ children, className = '', padded = true }) {
  return (
    <div className={`rounded-2xl ${THEME.card} shadow-xl shadow-black/20 ${padded ? 'p-6' : ''} ${className}`}>
      {children}
    </div>
  );
}

const BUTTON_VARIANTS = {
  primary: THEME.buttonPrimary,
  secondary: THEME.buttonSecondary,
  ghost: THEME.buttonGhost,
  danger: THEME.buttonDanger,
};

export function Button({ variant = 'primary', icon: Icon, loading, children, className = '', ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm ${BUTTON_VARIANTS[variant]} ${className}`}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : Icon ? <Icon className="w-4 h-4" /> : null}
      {children}
    </button>
  );
}

const BADGE_VARIANTS = {
  success: THEME.successBg + ' ' + THEME.success,
  error: THEME.errorBg + ' ' + THEME.error,
  warning: THEME.warningBg + ' ' + THEME.warning,
  info: THEME.infoBg + ' ' + THEME.info,
  neutral: THEME.neutralBg + ' text-neutral-400',
};

export function Badge({ status = 'neutral', icon: Icon, children }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-semibold uppercase tracking-wider ${BADGE_VARIANTS[status]}`}>
      {Icon && <Icon className="w-3 h-3" />}
      {children}
    </span>
  );
}

export function StatCard({ icon: Icon, label, value, sub }) {
  return (
    <div className={`p-6 rounded-2xl ${THEME.card} relative overflow-hidden group`}>
      <div className="absolute top-0 right-0 p-4 opacity-[0.06] group-hover:opacity-[0.1] transition-opacity">
        <Icon className="w-20 h-20 text-amber-400" strokeWidth={1} />
      </div>
      <div className="relative z-10">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400 mb-4 border border-amber-500/20">
          <Icon className="w-5 h-5" strokeWidth={1.75} />
        </div>
        <h3 className="text-3xl font-semibold text-neutral-50 mb-1 tracking-tight">{value}</h3>
        <p className="text-xs text-neutral-400 font-medium uppercase tracking-wider">{label}</p>
        {sub && <p className="text-xs text-neutral-600 mt-1.5">{sub}</p>}
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, subtitle }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      {Icon && (
        <div className="w-12 h-12 rounded-full bg-neutral-900 border border-white/[0.06] flex items-center justify-center mb-4">
          <Icon className="w-5 h-5 text-neutral-600" />
        </div>
      )}
      <p className="text-sm font-medium text-neutral-400">{title}</p>
      {subtitle && <p className="text-xs text-neutral-600 mt-1">{subtitle}</p>}
    </div>
  );
}

export function Spinner({ className = 'w-5 h-5' }) {
  return <Loader2 className={`${className} animate-spin text-amber-400`} />;
}

// A single-file dropzone slot, used wherever a screen needs several named
// upload targets side by side (e.g. Regular CGST / IGST, RCM CGST / IGST).
export function UploadSlot({ title, file, onChange, onRemove, accept = '.xlsx, .csv', icon: FileIcon }) {
  return (
    <div className={`relative border-2 border-dashed rounded-xl p-4 flex flex-col justify-center items-center text-center h-32 transition-colors ${file ? 'border-emerald-500/40 bg-emerald-500/[0.04]' : 'border-white/[0.1] bg-black/20 hover:border-amber-500/40'}`}>
      <input type="file" id={`slot-${title}`} className="hidden" accept={accept} onChange={onChange} />
      {file ? (
        <div className="w-full relative">
          <button onClick={onRemove} className="absolute -top-2 -right-2 text-neutral-500 hover:text-red-400"><X className="w-4 h-4" /></button>
          {FileIcon ? <FileIcon className="w-7 h-7 text-emerald-400 mx-auto mb-2" /> : <FileSpreadsheet className="w-7 h-7 text-emerald-400 mx-auto mb-2" />}
          <p className="text-xs text-emerald-400 font-medium truncate px-2">{file.name}</p>
        </div>
      ) : (
        <label htmlFor={`slot-${title}`} className="cursor-pointer w-full h-full flex flex-col items-center justify-center">
          <UploadIcon className="w-5 h-5 text-neutral-600 mb-2" />
          <span className="text-xs font-semibold text-neutral-400 uppercase tracking-wide">{title}</span>
          <span className="text-[10px] text-neutral-600 mt-1">Click to add</span>
        </label>
      )}
    </div>
  );
}
