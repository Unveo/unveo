from fastapi import FastAPI
from engine.score import priority_score
app = FastAPI()

@app.get("/api/works")
def works():
    return [{"name": "Road", "priority_score": priority_score({"severity": 0.7}, {})}]
