import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from .run_pipeline import run_pipeline
from .db import AsyncSessionLocal, init_db
from .models import Article
from sqlalchemy import select

app = FastAPI(title='News-to-Avatar Pipeline')

class RunResponse(BaseModel):
    message: str


@app.on_event('startup')
async def startup():
    # Ensure DB is initialized (no-op if already exists)
    await init_db()


@app.post('/run_pipeline', response_model=RunResponse)
async def run_pipeline_endpoint(topic: str = Query('technology'), limit: int = Query(5)):
    """Kick off the full pipeline: search -> scrape -> summarize -> script -> save"""
    try:
        await run_pipeline(topic, limit)
        return {"message": f"Pipeline run completed for topic '{topic}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/articles', response_model=List[dict])
async def get_articles(limit: int = 50):
    async with AsyncSessionLocal() as session:
        q = select(Article).limit(limit)
        res = await session.execute(q)
        rows = res.scalars().all()
        out = []
        for r in rows:
            out.append({
                'id': r.id,
                'title': r.title,
                'url': r.url,
                'summary': r.summary,
                'script': r.script,
                'video_url': r.video_url,
                'status': r.status,
                'created_at': r.created_at.isoformat() if r.created_at else None
            })
        return out

from .video_provider import build_did_payload, generate_video
from sqlalchemy import update


@app.post('/init-db')
async def init_db_endpoint():
    try:
        await init_db()
        return {"message": "db initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/generate-video/{article_id}')
async def generate_video_endpoint(article_id: int, model: str = 'expressive'):
    """Generate an avatar video for the given article ID using the configured provider."""
    async with AsyncSessionLocal() as session:
        q = select(Article).where(Article.id == article_id)
        res = await session.execute(q)
        article = res.scalar_one_or_none()
        if not article:
            raise HTTPException(status_code=404, detail='Article not found')
        if not article.script:
            raise HTTPException(status_code=400, detail='Article has no script to convert to video')

        payload = build_did_payload(article.script, model=model)
        try:
            resp = await generate_video(payload)
            # provider-specific: try common keys
            video_url = resp.get('result_url') or resp.get('video_url') or resp.get('id') or str(resp)
            article.video_url = video_url
            article.status = 'video_generated'
            session.add(article)
            await session.commit()
            return {'article_id': article.id, 'video_url': video_url, 'raw_response': resp}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
