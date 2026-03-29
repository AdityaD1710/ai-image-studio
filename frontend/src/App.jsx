import { useState } from "react";
import { Sparkles, Image as ImageIcon, Layers, Download, CheckCircle, AlertCircle } from "lucide-react";
import PromptInput from "./components/PromptInput";
import ImageCanvas from "./components/ImageCanvas";
import SegmentViewer from "./components/SegmentViewer";
import ResultPanel from "./components/ResultPanel";
import ProgressBar from "./components/ProgressBar";
import { generateImage } from "./api/client";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState("");
  const [result, setResult] = useState(null);
  const [baseImage, setBaseImage] = useState(null);
  const [maskB64, setMaskB64] = useState(null);

  async function handleGenerate(prompt, negPrompt, inpaintPrompt, enableInpaint, roomType) {
    setLoading(true);
    setStage("Processing AI Generation…");
    try {
      const data = await generateImage({
        prompt,
        negative_prompt: negPrompt,
        inpaint_prompt: inpaintPrompt || prompt,
        enable_inpaint: enableInpaint,
        room_type: roomType,
        mask_b64: maskB64,
      });
      setResult(data);
      // Store base image for comparison mode
      setBaseImage(`data:image/png;base64,${data.base_image}`);
    } catch (e) {
      console.error(e);
      alert("Generation failed: " + e.message);
    } finally {
      setLoading(false);
      setStage("");
    }
  }

  return (
    <div className="app">
      {/* Sidebar: Control Panel */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <Sparkles className="text-primary" size={24} />
          <h1>AI Image Studio</h1>
        </div>
        
        <PromptInput onGenerate={handleGenerate} disabled={loading} />
        
        {result && (
          <div className="control-panel" style={{ paddingTop: 0 }}>
            <div className="control-group">
              <label><Layers size={14} style={{ marginRight: 6 }} /> Scene Layers</label>
              <SegmentViewer segments={result.segments} />
            </div>
          </div>
        )}
      </aside>

      {/* Main: Creative Stage */}
      <main className="canvas-scene">
        {loading && <ProgressBar stage={stage} />}

        {!result && !loading && (
          <div className="panel" style={{ width: '100%', maxWidth: '600px', textAlign: 'center', marginTop: '10vh' }}>
            <ImageIcon size={48} style={{ color: 'var(--text-dim)', marginBottom: 16 }} />
            <h2 style={{ marginBottom: 12 }}>Ready to Create?</h2>
            <p style={{ color: 'var(--text-muted)' }}>Enter a prompt in the sidebar to generate your first AI interior design.</p>
          </div>
        )}

        {result && (
          <>
            <section className="panel" style={{ width: '100%', maxWidth: '1000px' }}>
              <h3 style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
                <ImageIcon size={20} className="text-accent" />
                Base Composition & Masking
              </h3>
              <ImageCanvas
                src={baseImage}
                segments={result.segments}
                onMaskChange={setMaskB64}
              />
            </section>

            <ResultPanel
              baseSrc={baseImage}
              editedSrc={`data:image/png;base64,${result.edited_image}`}
              finalSrc={`data:image/png;base64,${result.final_image}`}
              inpaintApplied={result.inpaint_applied}
            />
          </>
        )}
      </main>
    </div>
  );
}