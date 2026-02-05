import asyncio
import os
import argparse
import logging
import sys
from typing import List

logger = logging.getLogger(__name__)

async def run_pipeline(topic: str, limit: int = 5, use_playwright: bool = True):
    """
    Run the complete news-to-script pipeline
    """
    from gnews import GNews
    from .scraper import scrape_urls
    from .summarizer import summarize_article, generate_script
    from .db import AsyncSessionLocal
    from .models import Article

    print(f"🔎 Searching news for: {topic}")

    google_news = GNews(language='en', country='US', max_results=limit)

    try:
        news_items = google_news.get_news(topic)
        print(f"📰 Found {len(news_items)} news articles")
    except Exception as e:
        print(f"❌ GNews search failed: {e}")
        return

    if not news_items:
        print("⚠️  No articles found for this topic")
        return

    # ─── IMPORTANT CHANGE: Resolve real URLs ────────────────────────────────
    urls = []
    url_to_title = {}
    url_to_gnews_item = {}

    for item in news_items:
        gn_url = item.get('url') or item.get('link')
        if not gn_url:
            continue

        title = item.get('title', 'No title')

        real_url = gn_url
        try:
            full = google_news.get_full_article(gn_url)
            if full and hasattr(full, 'url') and full.url:
                real_url = full.url
                if hasattr(full, 'title') and full.title:
                    title = full.title
            print(f"  → Resolved: {real_url[:90]}...")
        except Exception as e:
            print(f"  ⚠️ get_full_article failed for {gn_url[:60]}... → {e}")

        urls.append(real_url)
        url_to_title[real_url] = title
        url_to_gnews_item[real_url] = item

    print(f"✅ Got {len(urls)} resolved article URLs")

    # ─── Scrape ──────────────────────────────────────────────────────────────
    print(f"\n📄 Scraping articles with Playwright (this may take a minute)...")
    scrape_results = await scrape_urls(urls, use_playwright=use_playwright)

    # ─── Process and save ────────────────────────────────────────────────────
    processed_count = 0
    async with AsyncSessionLocal() as session:
        for idx, scrape_result in enumerate(scrape_results, 1):
            final_url = scrape_result['url']
            status = scrape_result['status']
            content = scrape_result.get('content', '')
            title = scrape_result.get('title') or url_to_title.get(final_url, 'No title')

            print(f"\n{'='*70}")
            print(f"[{idx}/{len(scrape_results)}] {title[:65]}...")
            print(f"{'='*70}")

            if status != 'success' or len(content) < 300:
                error = scrape_result.get('error', 'Unknown reason')
                print(f"  ❌ Skipping: {error}")
                continue

            print(f"  ✅ Scraped: {len(content):,} chars")
            if final_url != urls[idx-1]:
                print(f"  🔗 Final URL: {final_url[:90]}...")

            try:
                print(f"  ⏳ Summarizing...")
                summary = await summarize_article(content)

                print(f"  ⏳ Generating script...")
                script = await generate_script(title, summary)

                print(f"  📝 Script preview: {script[:140].replace('\n',' ')}...")

                article = Article(
                    title=title,
                    url=final_url,
                    content=content[:15000],
                    summary=summary,
                    script=script,
                    status='ready'
                )
                session.add(article)
                processed_count += 1
                print(f"  💾 Saved")

            except Exception as e:
                print(f"  ❌ Processing error: {e}")
                logger.error(f"Article {idx} failed", exc_info=True)

        try:
            await session.commit()
            print(f"\n{'='*70}")
            print(f"✅ PIPELINE COMPLETED — {processed_count}/{len(scrape_results)} saved")
            print(f"{'='*70}\n")
        except Exception as e:
            print(f"❌ Commit failed: {e}")

# ─── CLI / Windows compatibility ────────────────────────────────────────────

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=str, default='technology')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--no-playwright', action='store_true')
    args = parser.parse_args()

    use_pw = not args.no_playwright

    if sys.platform == 'win32':
        print("🔧 Windows: using ProactorEventLoop")
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_pipeline(args.topic, args.limit, use_playwright=use_pw))
    else:
        asyncio.run(run_pipeline(args.topic, args.limit, use_playwright=use_pw))