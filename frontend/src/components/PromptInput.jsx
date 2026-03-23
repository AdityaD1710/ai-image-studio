import { useState } from "react";

export default function PromptInput({ onGenerate, disabled }) {
  const [prompt, setPrompt] = useState("");
  const [neg, setNeg] = useState("");
  const [inpaintPrompt, setInpaintPrompt] = useState("");

  return (
    <div className="prompt-panel">
      <textarea
        placeholder="Describe your image…"
        value={prompt}
        onChange={e => setPrompt(e.target.value)}
        rows={3}
      />
      <input
        placeholder="Negative prompt (optional)"
        value={neg}
        onChange={e => setNeg(e.target.value)}
      />
      <input
        placeholder="Inpaint prompt (defaults to main prompt)"
        value={inpaintPrompt}
        onChange={e => setInpaintPrompt(e.target.value)}
      />
      <button
        onClick={() => onGenerate(prompt, neg, inpaintPrompt)}
        disabled={disabled || !prompt.trim()}
      >
        {disabled ? "Generating…" : "Generate"}
      </button>
    </div>
  );
}