from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Autonomous AI Agent",
    version="1.0.0"
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "message":"Autonomous AI Agent Running 🚀"
    }