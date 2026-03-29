import { Layers } from "lucide-react";

export default function SegmentViewer({ segments }) {
  if (!segments?.length) return (
    <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontStyle: 'italic', marginTop: 8 }}>
      No visual segments detected yet...
    </div>
  );
  
  return (
    <div className="segment-layer-list">
      {segments.map((seg, i) => (
        <div key={i} className="layer-chip">
          <div className="dot" style={{ background: i % 2 === 0 ? 'var(--accent)' : 'var(--primary)' }}></div>
          <span>{seg.label}</span>
          <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>{(seg.confidence * 100).toFixed(0)}%</span>
        </div>
      ))}
    </div>
  );
}