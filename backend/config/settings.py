from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    REDIS_URL: str = "redis://localhost:6379/0"
    STORAGE_DIR: str = "../storage"
    WEIGHTS_DIR: str = "../storage/weights"

    # i5 laptop optimizations
    DEVICE: str = "cpu"         # change to "cuda" if you add a GPU later
    ENABLE_CPU_OFFLOAD: bool = True
    USE_FP16: bool = False      # fp16 unstable on CPU; set True for CUDA
    MAX_STEPS_SD15: int = 20    # fewer steps → faster on CPU
    MAX_STEPS_SDXL: int = 15

    SD15_MODEL: str = "runwayml/stable-diffusion-v1-5"
    SDXL_MODEL: str = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
    CONTROLNET_MODEL: str = "lllyasviel/sd-controlnet-canny"
    CONTROLNET_SDXL_MODEL: str = "diffusers/controlnet-canny-sdxl-1.0"
    SAM_CHECKPOINT: str = "../storage/weights/sam_vit_b_01ec64.pth"
    SAM_MODEL_TYPE: str = "vit_b"   # vit_b smallest — best for i5
    CLIP_MODEL: str = "openai/clip-vit-base-patch32"

    class Config:
        env_file = ".env"

settings = Settings()