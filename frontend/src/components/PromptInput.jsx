import { Sparkles, Terminal, Settings } from "lucide-react";
import { useState } from "react";

export default function PromptInput({ onGenerate, disabled }) {
  const [prompt, setPrompt] = useState("");
  const [neg, setNeg] = useState("");
  const [inpaintPrompt, setInpaintPrompt] = useState("");
  const [enableInpaint, setEnableInpaint] = useState(false);
  const [roomType, setRoomType] = useState("generic");

  return (
    <div className="control-panel">
      <div className="control-group">
        <label><Sparkles size={14} style={{ marginRight: 6 }} /> Visual Prompt</label>
        <textarea
          placeholder="Describe your dream room..."
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          rows={4}
          disabled={disabled}
        />
      </div>

      <div className="control-group">
        <label><Terminal size={14} style={{ marginRight: 6 }} /> Negative Prompt</label>
        <input
          type="text"
          placeholder="e.g. low quality, blurry"
          value={neg}
          onChange={e => setNeg(e.target.value)}
          disabled={disabled}
        />
      </div>

      <div className="control-group">
        <label><Settings size={14} style={{ marginRight: 6 }} /> Interior Settings</label>
        <select value={roomType} onChange={e => setRoomType(e.target.value)} disabled={disabled}>
          <option value="generic">Generic Interior</option>
          <option value="living_room">Living Room</option>
          <option value="bedroom">Bedroom</option>
          <option value="kitchen">Kitchen</option>
          <option value="dining_room">Dining Room</option>
          <option value="office">Office Studio</option>
        </select>
      </div>

      <div className="control-group">
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={enableInpaint}
            onChange={e => setEnableInpaint(e.target.checked)}
            disabled={disabled}
          />
          <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Enable High-Res Inpainting</span>
        </label>
        {enableInpaint && (
          <input
            type="text"
            style={{ marginTop: 8 }}
            placeholder="Inpaint focus (defaults to main)"
            value={inpaintPrompt}
            onChange={e => setInpaintPrompt(e.target.value)}
            disabled={disabled}
          />
        )}
      </div>

      <button
        className="btn-primary"
        onClick={() => onGenerate(prompt, neg, inpaintPrompt, enableInpaint, roomType)}
        disabled={disabled || !prompt.trim()}
      >
        {disabled ? "Synthesizing Image..." : (
          <>
            <Sparkles size={18} /> Generate Creation
          </>
        )}
      </button>
    </div>
  );
}