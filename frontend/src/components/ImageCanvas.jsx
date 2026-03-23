import { useRef, useEffect, useState } from "react";

export default function ImageCanvas({ src, onMaskChange }) {
  const canvasRef = useRef(null);
  const [drawing, setDrawing] = useState(false);

  useEffect(() => {
    if (!src) return;
    const img = new Image();
    img.src = src;
    img.onload = () => {
      const canvas = canvasRef.current;
      canvas.width = img.width;
      canvas.height = img.height;
      canvas.getContext("2d").drawImage(img, 0, 0);
    };
  }, [src]);

  function draw(e) {
    if (!drawing) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (canvas.width / rect.width);
    const y = (e.clientY - rect.top) * (canvas.height / rect.height);
    ctx.fillStyle = "rgba(255,0,0,0.5)";
    ctx.beginPath();
    ctx.arc(x, y, 20, 0, Math.PI * 2);
    ctx.fill();
  }

  function exportMask() {
    const canvas = canvasRef.current;
    const maskCanvas = document.createElement("canvas");
    maskCanvas.width = canvas.width;
    maskCanvas.height = canvas.height;
    const mCtx = maskCanvas.getContext("2d");
    const imgData = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height);
    const maskData = mCtx.createImageData(canvas.width, canvas.height);
    for (let i = 0; i < imgData.data.length; i += 4) {
      const isRed = imgData.data[i] > 200 && imgData.data[i + 1] < 100;
      const val = isRed ? 255 : 0;
      maskData.data[i] = maskData.data[i + 1] = maskData.data[i + 2] = val;
      maskData.data[i + 3] = 255;
    }
    mCtx.putImageData(maskData, 0, 0);
    const b64 = maskCanvas.toDataURL("image/png").split(",")[1];
    onMaskChange(b64);
  }

  return (
    <div className="canvas-container">
      <p className="hint">Paint a mask on the image to inpaint that region</p>
      <canvas
        ref={canvasRef}
        onMouseDown={() => setDrawing(true)}
        onMouseUp={() => { setDrawing(false); exportMask(); }}
        onMouseMove={draw}
        style={{ cursor: "crosshair", maxWidth: "100%" }}
      />
    </div>
  );
}