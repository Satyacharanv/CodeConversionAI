from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.code_conversion_route import router as code_conversion_router

app = FastAPI(title="Code Migration API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(code_conversion_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
