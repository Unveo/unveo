from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import joblib

app = FastAPI()
model = joblib.load("model.joblib")

@app.post("/predict")
def predict(text: str):
    label = model.predict([text])[0]
    confidence = float(model.predict_proba([text]).max())
    return {"category": label, "confidence": confidence}

@app.get("/health")
def health():
    return {"ok": True}

app.mount("/", StaticFiles(directory="static", html=True))
