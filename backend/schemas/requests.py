from pydantic import BaseModel
from typing import Optional

class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    inpaint_prompt: Optional[str] = None
    mask_b64: Optional[str] = None      # base64 PNG mask drawn by user
    steps_sd15: Optional[int] = 20
    steps_sdxl: Optional[int] = 15