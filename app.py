import os
import re
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import pymongo
from detoxify import Detoxify
import uvicorn
from bson import json_util
import json

app = FastAPI(title="Facebook Comments Toxicity Analyzer")

# MongoDB connection
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["facebook_comments"]
collection = db["toxicity_analysis"]

# Load Detoxify model
model = Detoxify('original')

class Comment(BaseModel):
    author: str
    date: str
    text: str
    url: str
    
class CommentAnalysis(BaseModel):
    author: str
    date: str
    text: str
    url: str
    toxicity: float
    severe_toxicity: float
    obscene: float
    threat: float
    insult: float
    identity_attack: float
    cleaned_text: str

def clean_text(text):
    """Clean and normalize text"""
    if text == "No text found":
        return ""
    
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove "En voir plus" and similar phrases
    text = re.sub(r'…\s*En voir plus', '', text)
    
    return text

def analyze_toxicity(text):
    """Analyze toxicity of text using Detoxify"""
    if not text or text == "":
        return {
            "toxicity": 0.0,
            "severe_toxicity": 0.0,
            "obscene": 0.0,
            "threat": 0.0,
            "insult": 0.0,
            "identity_attack": 0.0
        }
    
    results = model.predict(text)
    return {
        "toxicity": float(results["toxicity"]),
        "severe_toxicity": float(results["severe_toxicity"]),
        "obscene": float(results["obscene"]),
        "threat": float(results["threat"]),
        "insult": float(results["insult"]),
        "identity_attack": float(results["identity_attack"])
    }

def process_csv(file_path):
    """Process CSV file, analyze toxicity, and store in MongoDB"""
    try:
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Process each comment
        results = []
        for _, row in df.iterrows():
            # Skip rows with no text
            if row['text'] == "No text found":
                continue
                
            # Clean text
            cleaned_text = clean_text(row['text'])
            
            # Analyze toxicity
            toxicity_scores = analyze_toxicity(cleaned_text)
            
            # Create result object
            result = {
                "author": row['author'],
                "date": row['date'],
                "text": row['text'],
                "url": row['url'],
                "cleaned_text": cleaned_text,
                **toxicity_scores
            }
            
            # Add to results list
            results.append(result)
            
            # Insert into MongoDB
            collection.insert_one(result)
        
        # Save processed results to CSV
        results_df = pd.DataFrame(results)
        results_df.to_csv(file_path.replace('.csv', '_analyzed.csv'), index=False)
        
        return len(results)
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        raise e

@app.post("/upload-csv/", response_model=dict)
async def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload CSV file for processing"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Save uploaded file
    file_path = f"c:/Users/Ahmed/Desktop/fcb_scrap/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Process in background
    background_tasks.add_task(process_csv, file_path)
    
    return {"message": f"Processing {file.filename} in the background"}

@app.get("/comments/", response_model=List[dict])
async def get_comments(limit: int = 100, min_toxicity: Optional[float] = None):
    """Get analyzed comments from MongoDB"""
    query = {}
    if min_toxicity is not None:
        query["toxicity"] = {"$gte": min_toxicity}
    
    cursor = collection.find(query).limit(limit)
    results = list(cursor)
    
    # Convert ObjectId to string for JSON serialization
    return json.loads(json_util.dumps(results))

@app.get("/stats/")
async def get_stats():
    """Get statistics about the analyzed comments"""
    total_comments = collection.count_documents({})
    toxic_comments = collection.count_documents({"toxicity": {"$gte": 0.5}})
    severe_toxic_comments = collection.count_documents({"severe_toxicity": {"$gte": 0.5}})
    
    # Get average toxicity scores
    pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_toxicity": {"$avg": "$toxicity"},
                "avg_severe_toxicity": {"$avg": "$severe_toxicity"},
                "avg_obscene": {"$avg": "$obscene"},
                "avg_threat": {"$avg": "$threat"},
                "avg_insult": {"$avg": "$insult"},
                "avg_identity_attack": {"$avg": "$identity_attack"}
            }
        }
    ]
    
    avg_results = list(collection.aggregate(pipeline))
    avg_stats = avg_results[0] if avg_results else {}
    
    return {
        "total_comments": total_comments,
        "toxic_comments": toxic_comments,
        "severe_toxic_comments": severe_toxic_comments,
        "average_scores": {k: v for k, v in avg_stats.items() if k != "_id"} if avg_stats else {}
    }

@app.post("/analyze-text/")
async def analyze_text(text: str):
    """Analyze toxicity of a single text"""
    cleaned = clean_text(text)
    toxicity_scores = analyze_toxicity(cleaned)
    
    return {
        "original_text": text,
        "cleaned_text": cleaned,
        **toxicity_scores
    }

@app.get("/")
async def root():
    return {"message": "Facebook Comments Toxicity Analyzer API"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)