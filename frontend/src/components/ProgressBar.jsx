export default function ProgressBar({ stage }) {
  return (
    <div className="progress">
      <div className="bar" />
      <span>{stage}</span>
    </div>
  );
}