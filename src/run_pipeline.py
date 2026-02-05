import asyncio
import os
import argparse
import logging
from typing import List

logger = logging.getLogger(__name__)


async def run_pipeline(topic: str, limit: int = 5, use_playwright: bool = True):
    """
    Run the complete news-to-script pipeline with Playwright scraping.
    
    Playwright automatically:
    - Follows Google News redirects
    - Executes JavaScript
    - Extracts dynamic content
    
    Steps:
    1. Search Google News for the topic
    2. Get article URLs (even if they're Google News redirects)
    3. Use Playwright to navigate and scrape (follows redirects automatically)
    4. Generate summaries with LLM
    5. Create news anchor scripts
    6. Save to database
    """
    from gnews import GNews
    from .scraper import scrape_urls
    from .summarizer import summarize_article, generate_script
    from .db import AsyncSessionLocal
    from .models import Article
    
    print(f"🔎 Searching news for: {topic}")
    
    # Initialize GNews
    google_news = GNews(language='en', country='US', max_results=limit)
    
    # Search for news
    try:
        news_items = google_news.get_news(topic)
        print(f"📰 Found {len(news_items)} news articles")
    except Exception as e:
        print(f"❌ GNews search failed: {e}")
        return
    
    if not news_items:
        print("⚠️  No articles found for this topic")
        return
    
    # Extract URLs (even if they're redirects - Playwright will handle them)
    urls = []
    url_to_title = {}
    
    for item in news_items:
        url = item.get('url', '')
        if url:
            urls.append(url)
            url_to_title[url] = item.get('title', 'No title')
    
    print(f"✅ Got {len(urls)} article URLs")
    
    # Scrape all articles using Playwright
    print(f"\n📄 Scraping articles with Playwright (this may take a minute)...")
    print(f"💡 Playwright will automatically follow redirects and extract content")
    
    scrape_results = await scrape_urls(urls, use_playwright=use_playwright)
    
    # Process and save to database
    processed_count = 0
    async with AsyncSessionLocal() as session:
        for idx, scrape_result in enumerate(scrape_results, 1):
            # Get the final URL (after Playwright followed redirects)
            final_url = scrape_result['url']
            original_url = urls[idx - 1]
            
            status = scrape_result['status']
            content = scrape_result.get('content', '')
            title = scrape_result.get('title')
            
            # Use GNews title as fallback
            if not title:
                title = url_to_title.get(original_url, 'No title')
            
            print(f"\n{'='*60}")
            print(f"[{idx}/{len(scrape_results)}] {title[:60]}...")
            print(f"{'='*60}")
            
            # Skip if scraping failed
            if status != 'success' or not content or len(content) < 200:
                error = scrape_result.get('error', 'Unknown error')
                print(f"  ❌ Skipping: {error}")
                continue
            
            print(f"  ✅ Scraped: {len(content)} chars")
            if final_url != original_url:
                print(f"  🔗 Real URL: {final_url[:80]}...")
            
            try:
                # Generate summary
                print(f"  ⏳ Generating summary...")
                summary = await summarize_article(content)
                print(f"  ✅ Summary: {len(summary)} chars")
                
                # Generate script
                print(f"  ⏳ Generating news script...")
                script = await generate_script(title, summary)
                print(f"  ✅ Script: {len(script)} chars")
                
                # Preview script
                script_preview = script[:150].replace('\n', ' ')
                print(f"  📝 Preview: \"{script_preview}...\"")
                
                # Save to database
                article_record = Article(
                    title=title,
                    url=final_url,  # Use the real URL after redirect
                    content=content[:10000],  # Limit DB storage
                    summary=summary,
                    script=script,
                    status='ready'
                )
                session.add(article_record)
                processed_count += 1
                print(f"  💾 Saved to database")
                
            except Exception as e:
                print(f"  ❌ Error processing: {e}")
                logger.error(f"Error processing article {idx}: {e}", exc_info=True)
                continue
        
        # Commit all at once
        try:
            await session.commit()
            print(f"\n{'='*60}")
            print(f"✅ PIPELINE COMPLETED!")
            print(f"{'='*60}")
            print(f"📊 Successfully processed: {processed_count}/{len(scrape_results)} articles")
            print(f"💡 Articles are ready for video generation!")
            print(f"{'='*60}\n")
            
            if processed_count > 0:
                print(f"🎬 Next steps:")
                print(f"  1. Start API: uvicorn src.main:app --reload")
                print(f"  2. Open: http://localhost:8000/docs")
                print(f"  3. Test: GET /articles")
                print(f"  4. Generate video: POST /generate-video/1")
        except Exception as e:
            print(f"\n❌ Database commit failed: {e}")
            logger.error(f"Database commit error: {e}", exc_info=True)


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Run the news-to-avatar pipeline')
    parser.add_argument('--init-db', action='store_true', help='Initialize database')
    parser.add_argument('--topic', type=str, default='technology', help='News topic to search')
    parser.add_argument('--limit', type=int, default=5, help='Number of articles to process')
    parser.add_argument('--no-playwright', action='store_true', help='Disable Playwright (use fallback scrapers)')
    args = parser.parse_args()

    if args.init_db:
        from .db import init_db
        asyncio.run(init_db())
    else:
        use_playwright = not args.no_playwright
        asyncio.run(run_pipeline(args.topic, args.limit, use_playwright=use_playwright))