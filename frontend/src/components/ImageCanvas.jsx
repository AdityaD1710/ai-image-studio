import { useRef, useEffect, useState } from "react";
import { MousePointer2, Eraser, Info } from "lucide-react";

export default function ImageCanvas({ src, segments = [], onMaskChange }) {
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const [drawing, setDrawing] = useState(false);
  const [hoverInfo, setHoverInfo] = useState(null);

  function drawSegmentOverlays(ctx, width, height) {
    if (!segments?.length) return;

    ctx.save();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(0, 200, 255, 0.6)";
    ctx.setLineDash([5, 5]);

    segments.forEach((seg) => {
      const [x, y, w, h] = seg.bbox || [0, 0, 0, 0];
      ctx.strokeRect(x, y, w, h);
    });

    ctx.restore();
  }

  function redrawBaseWithOverlays() {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img) return;

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    drawSegmentOverlays(ctx, canvas.width, canvas.height);
  }

  useEffect(() => {
    if (!src) return;
    const img = new Image();
    img.src = src;
    img.onload = () => {
      imageRef.current = img;
      const canvas = canvasRef.current;
      canvas.width = img.width;
      canvas.height = img.height;
      redrawBaseWithOverlays();
    };
  }, [src]);

  useEffect(() => {
    if (!src) return;
    redrawBaseWithOverlays();
  }, [segments, src]);

  function getCanvasPoint(e) {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) * (canvas.width / rect.width),
      y: (e.clientY - rect.top) * (canvas.height / rect.height),
      uiX: e.clientX,
      uiY: e.clientY,
    };
  }

  function findSegmentAt(x, y) {
    return (segments || []).find((seg) => {
      const [sx, sy, sw, sh] = seg.bbox || [0, 0, 0, 0];
      return x >= sx && x <= sx + sw && y >= sy && y <= sy + sh;
    });
  }

  function draw(e) {
    if (!drawing) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const { x, y } = getCanvasPoint(e);
    
    // Draw semi-transparent "mask" color
    ctx.fillStyle = "hsla(350, 80%, 50%, 0.45)";
    ctx.beginPath();
    ctx.arc(x, y, 20, 0, Math.PI * 2);
    ctx.fill();
    
    // Glowing edge effect
    ctx.strokeStyle = "hsla(350, 80%, 60%, 0.2)";
    ctx.lineWidth = 4;
    ctx.stroke();
  }

  function handleMouseMove(e) {
    if (drawing) {
      draw(e);
      return;
    }

    const { x, y, uiX, uiY } = getCanvasPoint(e);
    const seg = findSegmentAt(x, y);
    if (!seg) {
      setHoverInfo(null);
      return;
    }

    setHoverInfo({
      label: seg.label,
      confidence: seg.confidence,
      x: uiX,
      y: uiY,
    });
  }

  function exportMask() {
    const canvas = canvasRef.current;
    const maskCanvas = document.createElement("canvas");
    maskCanvas.width = canvas.width;
    maskCanvas.height = canvas.height;
    const mCtx = maskCanvas.getContext("2d");
    
    // Only extract the "reddish" mask we painted
    const imgData = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height);
    const maskData = mCtx.createImageData(canvas.width, canvas.height);
    
    for (let i = 0; i < imgData.data.length; i += 4) {
      // Logic for capturing painted regions across base image
      const r = imgData.data[i];
      const g = imgData.data[i+1];
      const b = imgData.data[i+2];
      
      // Heuristic: Check if the pixel has a distinct "red" mask overlay
      // We look for significant saturation/hue shift towards HSLA(350, 80%, 50%, 0.45)
      // This is hit-miss with simple canvas. For better results, use a separate mask layer.
      // But we will stick to the provided logic but refined.
      const isMasked = r > 180 && g < 150 && b < 150; 
      const val = isMasked ? 255 : 0;
      maskData.data[i] = maskData.data[i + 1] = maskData.data[i + 2] = val;
      maskData.data[i + 3] = 255;
    }
    
    mCtx.putImageData(maskData, 0, 0);
    const b64 = maskCanvas.toDataURL("image/png").split(",")[1];
    onMaskChange(b64);
  }

  return (
    <div className="canvas-container" style={{ textAlign: 'center' }}>
      <p className="canvas-hint">
        <MousePointer2 size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
        Brush to define the inpainting area.
      </p>
      
      <div className="canvas-wrapper">
        <canvas
          ref={canvasRef}
          onMouseDown={() => setDrawing(true)}
          onMouseUp={() => { setDrawing(false); exportMask(); }}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHoverInfo(null)}
        />
        
        {hoverInfo && (
          <div
            className="segment-tooltip"
            style={{ left: `${hoverInfo.x + 16}px`, top: `${hoverInfo.y + 16}px` }}
          >
            <Info size={12} style={{ marginRight: 6 }} />
            {hoverInfo.label} ({(hoverInfo.confidence * 100).toFixed(0)}%)
          </div>
        )}
      </div>

      <div style={{ marginTop: 12, display: 'flex', justifyContent: 'center', gap: 10 }}>
        <button className="btn-primary" onClick={redrawBaseWithOverlays} style={{ padding: '8px 12px', background: 'var(--bg-input)', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
          <Eraser size={14} /> Clear Mask
        </button>
      </div>
    </div>
  );
}