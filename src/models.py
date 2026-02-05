from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from .db import Base

class Article(Base):
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=True)
    url = Column(String(1024), unique=True, nullable=False)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    script = Column(Text, nullable=True)
    video_url = Column(String(1024), nullable=True)
    status = Column(String(64), default='new')
    created_at = Column(DateTime, default=datetime.utcnow)
