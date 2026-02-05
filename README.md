# 🎥 News-to-Avatar Pipeline

**AI-powered news aggregation system that automatically converts news articles into AI avatar videos.**

## 📋 Project Overview

This system creates a complete end-to-end pipeline that:
1. 🔍 **Searches** for news articles using Google News
2. 📰 **Scrapes** full article content using Playwright
3. 🤖 **Summarizes** articles using OpenAI GPT-4
4. ✍️ **Generates** professional news scripts (30-45 seconds)
5. 🎬 **Creates** AI avatar videos with lip-sync using HeyGen
6. 💾 **Stores** everything in PostgreSQL database
7. 🌐 **Exposes** via FastAPI REST API with Swagger UI

---

## 🎯 Features

- ✅ **Automated News Discovery** - Search any topic on Google News
- ✅ **Smart Web Scraping** - Playwright handles JavaScript and redirects
- ✅ **LLM Summarization** - OpenAI generates factual summaries
- ✅ **Script Generation** - Creates broadcast-ready news scripts
- ✅ **AI Avatar Videos** - Your face speaking the news with perfect lip-sync
- ✅ **RESTful API** - Complete FastAPI backend with Swagger documentation
- ✅ **Database Storage** - PostgreSQL for all content and metadata
- ✅ **Male/Female Voices** - Customizable voice selection
- ✅ **Async/Await** - High-performance asynchronous architecture

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or 3.13
- PostgreSQL database
- OpenAI API key
- HeyGen account with API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo>
   cd AI_PROJECT
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Configure environment variables:**
   
   Create `.env` file in project root:
   ```env
   # OpenAI Configuration
   OPENAI_API_KEY=sk-proj-your-key-here
   OPENAI_MODEL=gpt-4o-mini
   
   # HeyGen Configuration
   HEYGEN_API_KEY=your-heygen-api-key
   HEYGEN_AVATAR_ID=your-avatar-id
   HEYGEN_VOICE_ID=2d5b0e6cf36349c0b48b282c8e2ff88b  # Male voice (default)
   
   # Database Configuration
   DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/newsdb
   ```

5. **Initialize database:**
   ```bash
   python -m src.run_pipeline --init-db
   ```

6. **Run the pipeline:**
   ```bash
   python -m src.run_pipeline --topic "technology" --limit 5
   ```

7. **Start the API server:**
   ```bash
   uvicorn src.main:app --reload
   ```

8. **Access Swagger UI:**
   ```
   http://localhost:8000/docs
   ```

---

## 🎤 Voice Configuration

### Available Voices

The system supports multiple voice options:

**Male Voices:**
- `male_professional` - Professional news anchor (default)
- `male_casual` - Casual conversational
- `male_news` - Formal news delivery

**Female Voices:**
- `female_professional` - Professional news anchor
- `female_casual` - Casual conversational
- `female_news` - Formal news delivery

### Setting Voice

**Option 1: Environment Variable (Global)**
```env
# In .env file
HEYGEN_VOICE_ID=2d5b0e6cf36349c0b48b282c8e2ff88b  # Male professional
```

**Option 2: Direct Voice ID**
```python
# In code
payload = build_did_payload(script, voice='male_professional')
```

### Voice IDs Reference

```python
VOICES = {
    'male_professional': '2d5b0e6cf36349c0b48b282c8e2ff88b',
    'male_casual': 'baf1c52778f0421585788312c4425a0e',
    'male_news': '40104aff703f4760bc2452535e0f9644',
    'female_professional': '1bd001e7e50f421d891986aad5158bc8',
    'female_casual': 'e7dd8cf4292f4c3b9e4c4c5e3f6c1e77',
    'female_news': 'af90abcf592b4e0e9d252eb5b5c0c3d5',
}
```

---

## 📚 API Documentation

### Endpoints

#### 1. Initialize Database
```http
POST /init-db
```
Creates the database tables.

**Response:**
```json
{
  "message": "db initialized"
}
```

#### 2. Run Complete Pipeline
```http
POST /run_pipeline?topic=technology&limit=5
```
Searches, scrapes, summarizes, and generates scripts for news articles.

**Parameters:**
- `topic` (string): News topic to search
- `limit` (integer): Number of articles to process

**Response:**
```json
{
  "message": "Pipeline run completed for topic 'technology'"
}
```

#### 3. Get All Articles
```http
GET /articles?limit=50
```
Retrieves all processed articles with summaries and scripts.

**Response:**
```json
[
  {
    "id": 1,
    "title": "AI Breakthrough in 2025",
    "url": "https://example.com/article",
    "summary": "Recent advances in AI...",
    "script": "Breaking news: Artificial intelligence...",
    "video_url": "https://resource.heygen.com/video/abc123.mp4",
    "status": "video_generated",
    "created_at": "2026-02-05T12:00:00"
  }
]
```

#### 4. Generate Avatar Video
```http
POST /generate-video/{article_id}?model=expressive
```
Generates AI avatar video for an article.

**Parameters:**
- `article_id` (path, integer): Article ID
- `model` (query, string): Voice model (optional)

**Response:**
```json
{
  "article_id": 1,
  "video_url": "https://resource.heygen.com/video/abc123.mp4",
  "raw_response": {
    "id": "tlk_abc123",
    "status": "done",
    "duration": 42.5,
    "provider": "heygen"
  }
}
```

---

## 🏗️ Project Structure

```
AI_PROJECT/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── run_pipeline.py         # Pipeline orchestrator
│   ├── gnews_searcher.py       # Google News search
│   ├── scraper.py              # Playwright web scraper
│   ├── summarizer.py           # OpenAI LLM integration
│   ├── video_provider.py       # HeyGen video generation
│   ├── models.py               # SQLAlchemy models
│   └── db.py                   # Database configuration
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🔄 Complete Workflow

### Step-by-Step Process

1. **News Discovery**
   ```
   GNews API → Search "technology" → Returns 5 article URLs
   ```

2. **Web Scraping**
   ```
   Playwright → Opens each URL → Executes JavaScript → Extracts content
   ```

3. **LLM Processing**
   ```
   OpenAI GPT-4 → Summarizes article → Generates news script
   ```

4. **Database Storage**
   ```
   PostgreSQL → Stores: title, URL, content, summary, script
   ```

5. **Video Generation**
   ```
   HeyGen API → Animates avatar → Generates video → Returns URL
   ```

6. **Final Result**
   ```
   Database updated with video URL → User can watch avatar speaking
   ```

---

## 📊 Database Schema

### Table: `articles`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| title | VARCHAR(512) | Article headline |
| url | VARCHAR(1024) | Article URL (unique) |
| content | TEXT | Full article text |
| summary | TEXT | LLM-generated summary |
| script | TEXT | News anchor script |
| video_url | VARCHAR(1024) | HeyGen video URL |
| status | VARCHAR(64) | Processing status |
| created_at | TIMESTAMP | Creation time |

**Status Values:**
- `new` - Just created
- `ready` - Has summary and script
- `video_generated` - Video created

---

## 🧪 Testing

### Test Pipeline
```bash
# Test with 2 articles
python -m src.run_pipeline --topic "AI" --limit 2
```

### Test API Endpoints
```bash
# Start server
uvicorn src.main:app --reload

# Test in browser
open http://localhost:8000/docs
```

### Test Video Generation
```bash
# In Python
python -c "import asyncio; from src.video_provider import test_voices; asyncio.run(test_voices())"
```

---

## 💰 Cost Breakdown

### Per 5 Articles

| Service | Cost | Notes |
|---------|------|-------|
| GNews | Free | No API key needed |
| OpenAI (Summaries) | ~$0.01 | GPT-4o-mini is very cheap |
| OpenAI (Scripts) | ~$0.01 | 5 scripts @ $0.002 each |
| HeyGen (Videos) | $0-0.50 | Free trial: 1 min credit |
| **Total** | **~$0.02** | *Excluding video after trial* |

### API Keys Needed

1. **OpenAI** - https://platform.openai.com/api-keys
   - Free tier: $5 credit
   - Cost: ~$0.002 per article
   
2. **HeyGen** - https://app.heygen.com/
   - Free trial: 1 minute video
   - Paid: $24/month for 15 minutes

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Playwright Not Working
```bash
# Install browsers
playwright install chromium

# If still fails, use Python 3.11
python3.11 -m venv .venv
```

#### 2. Database Connection Error
```bash
# Check PostgreSQL is running
psql -U postgres

# Verify DATABASE_URL in .env
# Format: postgresql+asyncpg://user:pass@host:port/dbname
```

#### 3. HeyGen API Error
```bash
# Verify API key
curl https://api.heygen.com/v1/user/remaining_quota \
  -H "x-api-key: your-key"

# Check avatar ID in HeyGen dashboard
```

#### 4. OpenAI Rate Limit
```bash
# Check usage: https://platform.openai.com/usage
# Add delay between requests if needed
```

#### 5. Scraping Returns Empty Content
```bash
# Try different topics (some sites block scrapers)
# Use broader topics: "technology", "AI", "space"
```

---

## 🎬 Demo Recording

### What to Show

1. **Terminal** - Run pipeline
   ```bash
   python -m src.run_pipeline --topic "technology" --limit 5
   ```

2. **Swagger UI** - Show all endpoints
   - GET /articles
   - POST /generate-video/1

3. **Video Result** - Open video URL
   - Show avatar speaking
   - Demonstrate lip-sync quality

### Recording Tips

- Use OBS Studio or Windows Game Bar
- Keep demo under 5 minutes
- Show end-to-end flow
- Explain architecture briefly

---

## 🔐 Security Notes

- Never commit `.env` file
- Use environment variables for secrets
- Rotate API keys regularly
- Use `.env.example` for templates

---

## 📈 Performance

- **Scraping**: ~5-10 seconds per article
- **Summarization**: ~2-3 seconds per article
- **Script Generation**: ~2-3 seconds per article
- **Video Generation**: ~30-90 seconds per video
- **Total**: ~5-10 minutes for 5 complete videos

---

## 🚀 Future Enhancements

- [ ] Add more video providers (D-ID, Synthesia)
- [ ] Support multiple languages
- [ ] Batch video generation
- [ ] Video thumbnail generation
- [ ] Email notifications
- [ ] Scheduled pipeline runs
- [ ] Admin dashboard
- [ ] Video analytics

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👤 Author

**Kashif**
- GitHub: [Your GitHub]
- LinkedIn: [Your LinkedIn]
- Email: [Your Email]

---

## 🙏 Acknowledgments

- **OpenAI** - GPT-4 for summarization
- **HeyGen** - AI avatar video generation
- **Playwright** - Web scraping automation
- **FastAPI** - Modern web framework

---

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review API documentation
3. Check HeyGen/OpenAI status pages
4. Create an issue on GitHub

---

## ✅ Checklist for Interview

- [x] Complete pipeline implemented
- [x] All APIs integrated (GNews, OpenAI, HeyGen)
- [x] Database with proper schema
- [x] RESTful API with Swagger docs
- [x] Async/await architecture
- [x] Error handling
- [x] Logging
- [x] Male voice option
- [x] Professional documentation
- [x] Working demo ready

---

**Built with ❤️ for AI-powered news automation**

🎯 **Ready for deployment!**