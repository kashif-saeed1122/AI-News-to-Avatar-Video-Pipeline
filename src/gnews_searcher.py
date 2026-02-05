import logging
from typing import List, Dict
from gnews import GNews
import re

logger = logging.getLogger(__name__)

class NewsSearcher:
    """
    Fetches articles using the GNews library (Google News RSS).
    Extracts real article URLs from Google News redirect links.
    """

    def __init__(self, topic: str, max_results: int = 5, language: str = 'en', country: str = 'US'):
        self.topic = topic
        self.google_news = GNews(language=language, country=country, max_results=max_results)

    def search(self) -> List[Dict]:
        """Returns list of dicts with keys: title, published date, url, publisher, etc."""
        try:
            logger.info(f"📰 Searching Google News for: {self.topic}")
            news_results = self.google_news.get_news(self.topic)
            
            # Extract real URLs from redirect links
            cleaned_results = []
            for item in news_results:
                # GNews returns articles with redirect URLs
                # We need to get the actual article using get_full_article
                try:
                    # Get full article which includes the real URL
                    full_article = self.google_news.get_full_article(item['url'])
                    
                    if full_article and hasattr(full_article, 'url'):
                        # Use the real URL from the full article
                        item['url'] = full_article.url
                        item['text'] = full_article.text if hasattr(full_article, 'text') else ''
                        cleaned_results.append(item)
                        logger.info(f"  ✅ Got article: {item.get('title', 'No title')[:60]}...")
                    else:
                        logger.warning(f"  ⚠️  Could not get full article for: {item.get('title', 'Unknown')}")
                        # Still add it with the redirect URL - scraper will try
                        cleaned_results.append(item)
                except Exception as e:
                    logger.warning(f"  ⚠️  Error getting full article: {e}")
                    # Still add it - scraper might work
                    cleaned_results.append(item)
            
            logger.info(f"✅ Found {len(cleaned_results)} news articles.")
            return cleaned_results
            
        except Exception as e:
            logger.error(f"❌ GNews Search Failed: {e}")
            return []