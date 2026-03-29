export default function ProgressBar({ stage }) {
  return (
    <div className="progress-overlay">
      <div className="spinner"></div>
      <p style={{ fontSize: '1.2rem', fontWeight: 600, color: 'white' }}>{stage}</p>
      <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: 8 }}>Please wait while the AI models process your request...</p>
    </div>
  );
}