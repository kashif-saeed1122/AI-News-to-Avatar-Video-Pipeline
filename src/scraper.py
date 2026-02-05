import asyncio
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Try to import Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - install with: pip install playwright && playwright install chromium")

# Try trafilatura as fallback
try:
    import trafilatura
    import requests
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

from bs4 import BeautifulSoup


async def scrape_url(url: str, use_playwright: bool = True) -> Dict:
    """
    Scrape a single URL with multiple strategies:
    1. Playwright (best - handles JS redirects and dynamic content)
    2. Trafilatura (good for static articles)
    3. BeautifulSoup (basic fallback)
    
    Returns:
        Dict with keys: url, title, content, status, error
    """
    item = {"url": url, "title": None, "content": "", "status": "failed", "error": None}
    
    try:
        # Try Playwright first (best for Google News and dynamic sites)
        if PLAYWRIGHT_AVAILABLE and use_playwright:
            result = await _scrape_with_playwright(url)
            if result['status'] == 'success':
                return result
            logger.info(f"  ⚠️  Playwright extraction weak, trying fallback...")
        
        # Fallback to trafilatura (good for static articles)
        if TRAFILATURA_AVAILABLE and not ('news.google.com' in url):
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: _scrape_with_trafilatura(url))
            if result['status'] == 'success':
                return result
        
        # Last resort: BeautifulSoup
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: _scrape_with_beautifulsoup(url))
        return result
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        item["error"] = str(e)
        return item


async def _scrape_with_playwright(url: str, timeout: int = 30000) -> Dict:
    """
    Scrape using Playwright - handles JavaScript, redirects, and dynamic content.
    This is the BEST method for Google News articles.
    """
    item = {"url": url, "title": None, "content": "", "status": "failed", "error": None}
    
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            # Navigate to URL (this automatically follows redirects)
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                
                # Wait a bit for JavaScript to execute
                await page.wait_for_timeout(2000)
                
                # Get the final URL after redirects
                final_url = page.url
                
                # Get title
                try:
                    title = await page.title()
                except:
                    title = None
                
                # Try to get main article content
                content = ""
                
                # Strategy 1: Look for article tag
                try:
                    article_element = await page.query_selector('article')
                    if article_element:
                        content = await article_element.inner_text()
                except:
                    pass
                
                # Strategy 2: Look for main tag
                if not content or len(content) < 200:
                    try:
                        main_element = await page.query_selector('main')
                        if main_element:
                            content = await main_element.inner_text()
                    except:
                        pass
                
                # Strategy 3: Get all paragraphs
                if not content or len(content) < 200:
                    try:
                        # Get text from all paragraph elements
                        paragraphs = await page.query_selector_all('p')
                        texts = []
                        for p in paragraphs:
                            text = await p.inner_text()
                            if text.strip():
                                texts.append(text.strip())
                        content = '\n\n'.join(texts)
                    except:
                        pass
                
                # Strategy 4: Last resort - get body text
                if not content or len(content) < 200:
                    try:
                        body = await page.query_selector('body')
                        if body:
                            content = await body.inner_text()
                    except:
                        pass
                
                # Clean up content
                content = ' '.join(content.split()) if content else ''
                
                # Validate
                if len(content) < 200:
                    item['status'] = 'short_content'
                    item['error'] = f"Content too short ({len(content)} chars)"
                else:
                    item['status'] = 'success'
                    logger.info(f"  ✅ Scraped (Playwright): {(title or 'No title')[:50]}... ({len(content)} chars)")
                
                item['url'] = final_url  # Use the final URL after redirect
                item['title'] = title
                item['content'] = content
                
            except Exception as e:
                item['error'] = f"Navigation failed: {str(e)}"
                logger.warning(f"  ❌ Playwright navigation failed: {e}")
            
            finally:
                await page.close()
                await context.close()
                await browser.close()
                
    except Exception as e:
        item['error'] = str(e)
        logger.error(f"  ❌ Playwright scraping failed: {e}")
    
    return item


def _scrape_with_trafilatura(url: str, timeout: int = 15) -> Dict:
    """Scrape using trafilatura - good for static articles"""
    item = {"url": url, "title": None, "content": "", "status": "failed", "error": None}
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        content = trafilatura.extract(response.text, include_comments=False, include_tables=False)
        metadata = trafilatura.extract_metadata(response.text)
        title = metadata.title if metadata and metadata.title else None
        
        if content and len(content) >= 200:
            item['status'] = 'success'
            item['content'] = content.strip()
            item['title'] = title
            logger.info(f"  ✅ Scraped (trafilatura): {(title or 'No title')[:50]}... ({len(content)} chars)")
        else:
            item['status'] = 'short_content'
            item['error'] = f"Content too short ({len(content or '')} chars)"
            
    except Exception as e:
        item['error'] = str(e)
        logger.warning(f"  ⚠️  Trafilatura failed: {e}")
    
    return item


def _scrape_with_beautifulsoup(url: str, timeout: int = 15) -> Dict:
    """Fallback scraper using BeautifulSoup"""
    item = {"url": url, "title": None, "content": "", "status": "failed", "error": None}
    
    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get title
        title_tag = soup.find('h1') or soup.find('title')
        title = title_tag.get_text().strip() if title_tag else 'No title'
        
        # Remove unwanted tags
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        # Get paragraphs
        article = soup.find('article') or soup.find('main') or soup.find('body')
        paragraphs = article.find_all('p') if article else soup.find_all('p')
        content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        content = ' '.join(content.split())
        
        if len(content) >= 200:
            item['status'] = 'success'
            logger.info(f"  ✅ Scraped (BeautifulSoup): {title[:50]}... ({len(content)} chars)")
        else:
            item['status'] = 'short_content'
            item['error'] = f"Content too short ({len(content)} chars)"
        
        item['title'] = title
        item['content'] = content
        
    except Exception as e:
        item['error'] = str(e)
        logger.warning(f"  ❌ BeautifulSoup failed: {e}")
    
    return item


async def scrape_urls(urls: List[str], use_playwright: bool = True) -> List[Dict]:
    """
    Scrape multiple URLs.
    
    Args:
        urls: List of URLs to scrape
        use_playwright: Whether to use Playwright (slower but more reliable)
    
    Returns:
        List of scrape results
    """
    # For Playwright, process sequentially to avoid too many browser instances
    if use_playwright and PLAYWRIGHT_AVAILABLE:
        results = []
        for url in urls:
            result = await scrape_url(url, use_playwright=True)
            results.append(result)
        return results
    else:
        # For other methods, process concurrently
        tasks = [scrape_url(url, use_playwright=False) for url in urls]
        return await asyncio.gather(*tasks)


def scrape_urls_sync(urls: list, use_playwright: bool = True):
    """Synchronous wrapper"""
    return asyncio.run(scrape_urls(urls, use_playwright=use_playwright))


# Test function
async def test_scraper():
    """Test the scraper with various URLs"""
    test_urls = [
        "https://www.bbc.com/news/technology",
        "https://techcrunch.com/",
    ]
    
    results = await scrape_urls(test_urls, use_playwright=True)
    for result in results:
        print(f"\nURL: {result['url']}")
        print(f"Status: {result['status']}")
        print(f"Title: {result.get('title', 'None')[:60]}")
        print(f"Content length: {len(result.get('content', ''))}")
        if result.get('error'):
            print(f"Error: {result['error']}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_scraper())