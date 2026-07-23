import React, { useState, useRef, useEffect } from 'react';
import { ScrollText, Plus, Trash2, Download, Info } from 'lucide-react';
import { PageHeader, Card, Button } from '../components/ui';

// Self-contained resume stylesheet -- used for BOTH the on-screen preview and
// the print window, so what you see is exactly what prints. Deliberately not
// Tailwind (the print window has no Tailwind), and styled as a classic
// banking/IB resume: single column, serif, section rules, one page.
const RESUME_CSS = `
.resume-sheet {
  width: 794px; min-height: 1123px; box-sizing: border-box;
  background: #ffffff; color: #111111;
  padding: 48px 56px; margin: 0 auto;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 12.5px; line-height: 1.4;
}
.r-name { text-align: center; font-size: 24px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
.r-title { text-align: center; font-size: 12.5px; font-style: italic; color: #333; margin-top: 2px; }
.r-contact { text-align: center; font-size: 11px; color: #222; margin-top: 6px; }
.r-summary { font-size: 12px; text-align: justify; margin-top: 4px; }
.r-section-title {
  font-size: 12.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
  border-bottom: 1.4px solid #111; padding-bottom: 2px; margin: 16px 0 8px;
}
.r-entry { margin-bottom: 9px; }
.r-entry-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.r-strong { font-weight: 700; }
.r-right { font-size: 11px; color: #222; white-space: nowrap; }
.r-entry-sub { font-style: italic; font-size: 12px; color: #222; margin-top: 1px; }
.r-bullets { margin: 4px 0 0; padding-left: 18px; }
.r-bullets li { margin-bottom: 2px; }
.r-skill-line { margin-bottom: 3px; }
.r-skill-label { font-weight: 700; }
`;

const STORAGE_KEY = 'ORIGIN_RESUME_V1';

// Example content tailored to a CA moving into finance/IB -- illustrates the
// target format; every field is editable and meant to be replaced.
const DEFAULT_DATA = {
  name: 'Your Name',
  title: 'Chartered Accountant | Aspiring Investment Banking Analyst',
  phone: '+91 90000 00000',
  email: 'you@email.com',
  linkedin: 'linkedin.com/in/yourname',
  location: 'Mumbai, India',
  summary: '',
  education: [
    { institution: 'The Institute of Chartered Accountants of India (ICAI)', degree: 'Chartered Accountant (CA)', year: '2024', detail: 'Cleared all levels; AIR / percentage if notable' },
    { institution: 'University Name', degree: 'B.Com (Honours), Accounting & Finance', year: '2021', detail: 'CGPA 8.5 / 10' },
  ],
  experience: [
    {
      company: 'Firm / Employer Name', role: 'Article Assistant / Associate', location: 'Mumbai', start: 'Jul 2021', end: 'Present',
      bullets: [
        'Managed GST & TDS compliance for a portfolio of 15+ clients with combined turnover of ₹300+ crore, ensuring 100% on-time filings.',
        'Built an in-house tax-automation platform (Python/React) that cut monthly reconciliation time by ~70% across the practice.',
        'Led GSTR-2B vs books reconciliations recovering ₹40+ lakh of previously unclaimed input tax credit for clients.',
      ],
    },
  ],
  projects: [
    { name: 'Origin — Tax Automation Platform', detail: 'Full-stack Flask/React app automating GST (GSTR-1/2B/3B/9) and TDS workflows; in active use in practice.' },
  ],
  skills: {
    technical: 'Advanced Excel, Financial Modelling, Python, SQL, Tally, Zoho Books, Odoo',
    finance: 'Financial Statement Analysis, Valuation (DCF), GST & Direct Tax, Audit',
    certifications: 'Chartered Accountant (ICAI)',
    languages: 'English, Hindi',
    interests: 'Capital markets, financial technology',
  },
};

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULT_DATA, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return DEFAULT_DATA;
}

export default function Resume() {
  const [data, setData] = useState(load);
  const resumeRef = useRef(null);

  useEffect(() => {
    const t = setTimeout(() => {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch { /* ignore */ }
    }, 400);
    return () => clearTimeout(t);
  }, [data]);

  const set = (field, value) => setData(d => ({ ...d, [field]: value }));
  const setSkill = (field, value) => setData(d => ({ ...d, skills: { ...d.skills, [field]: value } }));

  // ---- list helpers (education / experience / projects) ----
  const addEdu = () => setData(d => ({ ...d, education: [...d.education, { institution: '', degree: '', year: '', detail: '' }] }));
  const setEdu = (i, k, v) => setData(d => ({ ...d, education: d.education.map((e, idx) => idx === i ? { ...e, [k]: v } : e) }));
  const delEdu = (i) => setData(d => ({ ...d, education: d.education.filter((_, idx) => idx !== i) }));

  const addExp = () => setData(d => ({ ...d, experience: [...d.experience, { company: '', role: '', location: '', start: '', end: '', bullets: [''] }] }));
  const setExp = (i, k, v) => setData(d => ({ ...d, experience: d.experience.map((e, idx) => idx === i ? { ...e, [k]: v } : e) }));
  const delExp = (i) => setData(d => ({ ...d, experience: d.experience.filter((_, idx) => idx !== i) }));
  const setBullet = (ei, bi, v) => setData(d => ({ ...d, experience: d.experience.map((e, idx) => idx === ei ? { ...e, bullets: e.bullets.map((b, j) => j === bi ? v : b) } : e) }));
  const addBullet = (ei) => setData(d => ({ ...d, experience: d.experience.map((e, idx) => idx === ei ? { ...e, bullets: [...e.bullets, ''] } : e) }));
  const delBullet = (ei, bi) => setData(d => ({ ...d, experience: d.experience.map((e, idx) => idx === ei ? { ...e, bullets: e.bullets.filter((_, j) => j !== bi) } : e) }));

  const addProj = () => setData(d => ({ ...d, projects: [...d.projects, { name: '', detail: '' }] }));
  const setProj = (i, k, v) => setData(d => ({ ...d, projects: d.projects.map((e, idx) => idx === i ? { ...e, [k]: v } : e) }));
  const delProj = (i) => setData(d => ({ ...d, projects: d.projects.filter((_, idx) => idx !== i) }));

  const downloadPdf = () => {
    const node = resumeRef.current;
    if (!node) return;
    const html =
      `<!doctype html><html><head><title>${(data.name || 'Resume').replace(/</g, '')}</title>` +
      `<style>${RESUME_CSS}\n@page{size:A4;margin:0;}\nhtml,body{margin:0;background:#fff;}\n.resume-sheet{box-shadow:none;margin:0;}</style>` +
      `</head><body>${node.outerHTML}</body></html>`;

    // A hidden iframe (not a popup) so no popup blocker can stop it. The
    // browser's print dialog opens over the page -> choose "Save as PDF".
    const existing = document.getElementById('resume-print-frame');
    if (existing) existing.remove();
    const iframe = document.createElement('iframe');
    iframe.id = 'resume-print-frame';
    iframe.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
    document.body.appendChild(iframe);

    const doc = iframe.contentWindow.document;
    doc.open();
    doc.write(html);
    doc.close();

    // document.write's load timing is unreliable, so trigger print on a
    // short delay once the markup + fonts have settled.
    setTimeout(() => {
      try {
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
      } catch (e) {
        alert('Could not open the print dialog. Please try again.');
      }
    }, 350);
  };

  const contact = [data.phone, data.email, data.linkedin, data.location].filter(Boolean).join('  |  ');
  const inputCls = 'w-full bg-black/30 border border-white/[0.08] rounded-md px-2.5 py-1.5 text-xs text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/50 transition-colors';
  const labelCls = 'text-[10px] font-semibold text-neutral-500 uppercase tracking-wider';

  return (
    <div className="max-w-[1400px] mx-auto space-y-6 animate-in fade-in duration-500">
      <PageHeader
        icon={ScrollText}
        eyebrow="Workspace"
        title="Resume Builder"
        subtitle="One-page finance / investment-banking format — autosaves as you type"
        action={<Button icon={Download} onClick={downloadPdf}>Download PDF</Button>}
      />

      <div className="flex items-start gap-2 p-3 bg-indigo-500/[0.06] border border-indigo-500/20 rounded-lg">
        <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <p className="text-[11px] text-neutral-400 leading-relaxed">
          Built to the banking convention: <b className="text-neutral-300">strict one page</b>, Education first, quantified impact bullets, ATS-friendly (real selectable text). Keep bullets results-driven (numbers, ₹, %). "Download PDF" opens a print window — choose <b className="text-neutral-300">Save as PDF</b> as the destination.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ---------------- FORM ---------------- */}
        <div className="space-y-5">
          <Card>
            <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider mb-4">Header</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2"><label className={labelCls}>Full Name</label><input className={inputCls} value={data.name} onChange={e => set('name', e.target.value)} /></div>
              <div className="col-span-2"><label className={labelCls}>Title / Tagline</label><input className={inputCls} value={data.title} onChange={e => set('title', e.target.value)} /></div>
              <div><label className={labelCls}>Phone</label><input className={inputCls} value={data.phone} onChange={e => set('phone', e.target.value)} /></div>
              <div><label className={labelCls}>Email</label><input className={inputCls} value={data.email} onChange={e => set('email', e.target.value)} /></div>
              <div><label className={labelCls}>LinkedIn</label><input className={inputCls} value={data.linkedin} onChange={e => set('linkedin', e.target.value)} /></div>
              <div><label className={labelCls}>Location</label><input className={inputCls} value={data.location} onChange={e => set('location', e.target.value)} /></div>
              <div className="col-span-2"><label className={labelCls}>Summary (optional — banks often skip it)</label><textarea className={inputCls + ' h-16 resize-none'} value={data.summary} onChange={e => set('summary', e.target.value)} placeholder="1–2 lines. Leave blank for a classic banking layout." /></div>
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider">Education</h3>
              <button onClick={addEdu} className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300"><Plus className="w-3.5 h-3.5" /> Add</button>
            </div>
            <div className="space-y-4">
              {data.education.map((e, i) => (
                <div key={i} className="space-y-2 pb-3 border-b border-white/[0.05] last:border-0">
                  <div className="flex gap-2">
                    <input className={inputCls} placeholder="Institution" value={e.institution} onChange={ev => setEdu(i, 'institution', ev.target.value)} />
                    <input className={inputCls + ' w-24'} placeholder="Year" value={e.year} onChange={ev => setEdu(i, 'year', ev.target.value)} />
                    <button onClick={() => delEdu(i)} className="text-neutral-600 hover:text-red-400 shrink-0"><Trash2 className="w-4 h-4" /></button>
                  </div>
                  <input className={inputCls} placeholder="Degree / Qualification" value={e.degree} onChange={ev => setEdu(i, 'degree', ev.target.value)} />
                  <input className={inputCls} placeholder="Detail (grade, rank, honours)" value={e.detail} onChange={ev => setEdu(i, 'detail', ev.target.value)} />
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider">Professional Experience</h3>
              <button onClick={addExp} className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300"><Plus className="w-3.5 h-3.5" /> Add</button>
            </div>
            <div className="space-y-5">
              {data.experience.map((x, i) => (
                <div key={i} className="space-y-2 pb-4 border-b border-white/[0.05] last:border-0">
                  <div className="flex gap-2">
                    <input className={inputCls} placeholder="Company" value={x.company} onChange={ev => setExp(i, 'company', ev.target.value)} />
                    <button onClick={() => delExp(i)} className="text-neutral-600 hover:text-red-400 shrink-0"><Trash2 className="w-4 h-4" /></button>
                  </div>
                  <input className={inputCls} placeholder="Role / Designation" value={x.role} onChange={ev => setExp(i, 'role', ev.target.value)} />
                  <div className="grid grid-cols-3 gap-2">
                    <input className={inputCls} placeholder="Location" value={x.location} onChange={ev => setExp(i, 'location', ev.target.value)} />
                    <input className={inputCls} placeholder="Start" value={x.start} onChange={ev => setExp(i, 'start', ev.target.value)} />
                    <input className={inputCls} placeholder="End" value={x.end} onChange={ev => setExp(i, 'end', ev.target.value)} />
                  </div>
                  <div className="space-y-1.5 pl-1">
                    {x.bullets.map((b, bi) => (
                      <div key={bi} className="flex gap-2 items-start">
                        <span className="text-neutral-600 text-xs mt-2">•</span>
                        <textarea className={inputCls + ' h-12 resize-none'} placeholder="Quantified, action-led bullet…" value={b} onChange={ev => setBullet(i, bi, ev.target.value)} />
                        <button onClick={() => delBullet(i, bi)} className="text-neutral-600 hover:text-red-400 shrink-0 mt-1.5"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                    ))}
                    <button onClick={() => addBullet(i)} className="text-[11px] text-indigo-400 hover:text-indigo-300 ml-4">+ bullet</button>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider">Projects</h3>
              <button onClick={addProj} className="flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300"><Plus className="w-3.5 h-3.5" /> Add</button>
            </div>
            <div className="space-y-3">
              {data.projects.map((p, i) => (
                <div key={i} className="flex gap-2 items-start">
                  <div className="flex-1 space-y-2">
                    <input className={inputCls} placeholder="Project name" value={p.name} onChange={ev => setProj(i, 'name', ev.target.value)} />
                    <textarea className={inputCls + ' h-12 resize-none'} placeholder="One-line description" value={p.detail} onChange={ev => setProj(i, 'detail', ev.target.value)} />
                  </div>
                  <button onClick={() => delProj(i)} className="text-neutral-600 hover:text-red-400 shrink-0"><Trash2 className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider mb-4">Skills & Additional</h3>
            <div className="space-y-3">
              <div><label className={labelCls}>Technical</label><input className={inputCls} value={data.skills.technical} onChange={e => setSkill('technical', e.target.value)} /></div>
              <div><label className={labelCls}>Finance</label><input className={inputCls} value={data.skills.finance} onChange={e => setSkill('finance', e.target.value)} /></div>
              <div><label className={labelCls}>Certifications</label><input className={inputCls} value={data.skills.certifications} onChange={e => setSkill('certifications', e.target.value)} /></div>
              <div><label className={labelCls}>Languages</label><input className={inputCls} value={data.skills.languages} onChange={e => setSkill('languages', e.target.value)} /></div>
              <div><label className={labelCls}>Interests</label><input className={inputCls} value={data.skills.interests} onChange={e => setSkill('interests', e.target.value)} /></div>
            </div>
          </Card>
        </div>

        {/* ---------------- PREVIEW ---------------- */}
        <div className="lg:sticky lg:top-4 self-start">
          <div className="rounded-lg overflow-hidden border border-white/[0.08] bg-neutral-800/40" style={{ maxHeight: '82vh', overflowY: 'auto' }}>
            <style>{RESUME_CSS}</style>
            {/* zoom scales the preview and reserves the correct (scaled) space;
                the ref'd sheet itself stays unscaled, so print gets clean A4 */}
            <div style={{ zoom: 0.66 }}>
                <div className="resume-sheet" ref={resumeRef}>
                  <div className="r-name">{data.name || 'Your Name'}</div>
                  {data.title && <div className="r-title">{data.title}</div>}
                  {contact && <div className="r-contact">{contact}</div>}

                  {data.summary && (<><div className="r-section-title">Summary</div><div className="r-summary">{data.summary}</div></>)}

                  {data.education.some(e => e.institution || e.degree) && <div className="r-section-title">Education</div>}
                  {data.education.map((e, i) => (e.institution || e.degree) && (
                    <div className="r-entry" key={i}>
                      <div className="r-entry-head"><span className="r-strong">{e.institution}</span><span className="r-right">{e.year}</span></div>
                      <div className="r-entry-sub">{e.degree}{e.detail ? `  —  ${e.detail}` : ''}</div>
                    </div>
                  ))}

                  {data.experience.some(x => x.company || x.role) && <div className="r-section-title">Professional Experience</div>}
                  {data.experience.map((x, i) => (x.company || x.role) && (
                    <div className="r-entry" key={i}>
                      <div className="r-entry-head">
                        <span className="r-strong">{x.company}</span>
                        <span className="r-right">{[x.location, [x.start, x.end].filter(Boolean).join(' – ')].filter(Boolean).join('  |  ')}</span>
                      </div>
                      {x.role && <div className="r-entry-sub">{x.role}</div>}
                      {x.bullets.some(Boolean) && (
                        <ul className="r-bullets">{x.bullets.filter(Boolean).map((b, bi) => <li key={bi}>{b}</li>)}</ul>
                      )}
                    </div>
                  ))}

                  {data.projects.some(p => p.name || p.detail) && <div className="r-section-title">Projects</div>}
                  {data.projects.map((p, i) => (p.name || p.detail) && (
                    <div className="r-entry" key={i}>
                      <div className="r-entry-head"><span className="r-strong">{p.name}</span></div>
                      {p.detail && <div className="r-summary">{p.detail}</div>}
                    </div>
                  ))}

                  {(data.skills.technical || data.skills.finance || data.skills.certifications || data.skills.languages || data.skills.interests) && (
                    <>
                      <div className="r-section-title">Skills &amp; Additional</div>
                      {data.skills.technical && <div className="r-skill-line"><span className="r-skill-label">Technical: </span>{data.skills.technical}</div>}
                      {data.skills.finance && <div className="r-skill-line"><span className="r-skill-label">Finance: </span>{data.skills.finance}</div>}
                      {data.skills.certifications && <div className="r-skill-line"><span className="r-skill-label">Certifications: </span>{data.skills.certifications}</div>}
                      {data.skills.languages && <div className="r-skill-line"><span className="r-skill-label">Languages: </span>{data.skills.languages}</div>}
                      {data.skills.interests && <div className="r-skill-line"><span className="r-skill-label">Interests: </span>{data.skills.interests}</div>}
                    </>
                  )}
                </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
