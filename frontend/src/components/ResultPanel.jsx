export default function ResultPanel({ editedSrc, finalSrc }) {
  return (
    <div className="result-panel">
      <div className="result-col">
        <h3>ControlNet Edited</h3>
        <img src={editedSrc} alt="edited" />
        <a href={editedSrc} download="edited.png">Download</a>
      </div>
      <div className="result-col">
        <h3>SDXL Inpainted</h3>
        <img src={finalSrc} alt="final" />
        <a href={finalSrc} download="final.png">Download</a>
      </div>
    </div>
  );
}