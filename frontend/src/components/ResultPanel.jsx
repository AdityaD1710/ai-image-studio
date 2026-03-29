import { Download, LayoutPanelLeft, Columns } from "lucide-react";
import { useState } from "react";

export default function ResultPanel({ baseSrc, editedSrc, finalSrc, inpaintApplied }) {
  const [compareMode, setCompareMode] = useState(true);

  return (
    <section className="result-section panel">
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <SparklesIcon size={20} className="text-primary" />
          AI Generation Results
        </h3>
        
        <div style={{ display: 'flex', gap: 8, background: 'var(--bg-input)', padding: 4, borderRadius: 8 }}>
          <button 
            className={`btn-toggle ${compareMode ? 'active' : ''}`}
            onClick={() => setCompareMode(true)}
            title="Comparison View"
          >
            <Columns size={16} />
          </button>
          <button 
            className={`btn-toggle ${!compareMode ? 'active' : ''}`}
            onClick={() => setCompareMode(false)}
            title="Single Final View"
          >
            <LayoutPanelLeft size={16} />
          </button>
        </div>
      </header>

      <div className={compareMode ? "comparison-mode" : "single-view"}>
        {compareMode && (
          <div className="result-card">
            <div className="badge">BEFORE</div>
            <img src={baseSrc} alt="Original composition" />
          </div>
        )}

        <div className="result-card">
          <div className="badge" style={{ color: 'var(--primary)' }}>
            {inpaintApplied ? "SDXL INPAINTED" : "AI FINAL"}
          </div>
          <img src={finalSrc} alt="AI Generated Result" />
          
          <div style={{ padding: 16, display: 'flex', justifyContent: 'flex-end' }}>
            <a href={finalSrc} download="studio_creation.png" className="btn-primary" style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
              <Download size={16} /> Export High-Res
            </a>
          </div>
        </div>
      </div>
      
      {!compareMode && (
        <div style={{ marginTop: 12, textAlign: 'center' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            <InfoIcon size={10} style={{ marginRight: 4 }} />
            Switch to Comparison Mode to see the transformation from the original composition.
          </p>
        </div>
      )}

      {/* Legacy/Debug Column for Edited Source if needed */}
      {/* 
      <div className="result-card">
          <div className="badge">CN EDITED</div>
          <img src={editedSrc} alt="ControlNet edit" />
      </div> 
      */}
    </section>
  );
}

// Internal icons helper to avoid import errors if not exported
function SparklesIcon({ size, className }) {
  return <span className={className}><svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg></span>;
}

function InfoIcon({ size, style }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={style}><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>;
}