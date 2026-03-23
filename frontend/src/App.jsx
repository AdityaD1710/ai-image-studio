import { useState } from "react";
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
  const [maskB64, setMaskB64] = useState(null);

  async function handleGenerate(prompt, negPrompt, inpaintPrompt) {
    setLoading(true);
    setStage("Generating base image…");
    try {
      const data = await generateImage({
        prompt,
        negative_prompt: negPrompt,
        inpaint_prompt: inpaintPrompt || prompt,
        mask_b64: maskB64,
      });
      setResult(data);
    } catch (e) {
      alert("Error: " + e.message);
    } finally {
      setLoading(false);
      setStage("");
    }
  }

  return (
    <div className="app">
      <header><h1>AI Image Studio</h1></header>
      <PromptInput onGenerate={handleGenerate} disabled={loading} />
      {loading && <ProgressBar stage={stage} />}
      {result && (
        <>
          <ImageCanvas
            src={`data:image/png;base64,${result.base_image}`}
            onMaskChange={setMaskB64}
          />
          <SegmentViewer segments={result.segments} />
          <ResultPanel
            editedSrc={`data:image/png;base64,${result.edited_image}`}
            finalSrc={`data:image/png;base64,${result.final_image}`}
          />
        </>
      )}
    </div>
  );
}