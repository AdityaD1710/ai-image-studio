from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.generate import router as gen_router
import uvicorn

app = FastAPI(title="AI Image Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gen_router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    # Use a single process by default on Windows to avoid noisy reload subprocess traces.
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)