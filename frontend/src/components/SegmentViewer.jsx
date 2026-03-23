export default function SegmentViewer({ segments }) {
  if (!segments?.length) return null;
  return (
    <div className="segment-list">
      <h3>Detected Segments</h3>
      <div className="segment-grid">
        {segments.map((seg, i) => (
          <div key={i} className="segment-chip">
            <span className="label">{seg.label}</span>
            <span className="conf">{(seg.confidence * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}