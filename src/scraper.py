import asyncio
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed → pip install playwright && playwright install chromium")

try:
    import trafilatura
    import requests
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

from bs4 import BeautifulSoup


async def scrape_url(url: str, use_playwright: bool = True) -> Dict:
    item = {"url": url, "title": None, "content": "", "status": "failed", "error": None}

    if PLAYWRIGHT_AVAILABLE and use_playwright:
        result = await _scrape_with_playwright(url)
        if result['status'] == 'success' and len(result['content']) >= 300:
            return result
        logger.info(f"  ⚠️ Playwright weak ({len(result['content'])} chars) → fallback")

    if TRAFILATURA_AVAILABLE:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: _scrape_with_trafilatura(url))
        if result['status'] == 'success' and len(result['content']) >= 300:
            return result

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: _scrape_with_beautifulsoup(url))
    return result


async def _scrape_with_playwright(url: str, timeout: int = 75000) -> Dict:
    item = {"url": url, "title": None, "content": "", "status": "failed", "error": None}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=[
                "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"
            ])
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 900},
            )
            page = await context.new_page()

            try:
                # ─── Navigation with consent handling ───────────────────────
                await page.goto(url, wait_until='domcontentloaded', timeout=timeout)

                # Try to click Google / cookie consent
                try:
                    consent = await page.query_selector(
                        'button:has-text("Accept all"), button:has-text("I agree"), #L2AGLb, [aria-label*="Accept"], [data-testid*="accept"]'
                    )
                    if consent:
                        await consent.click(delay=200)
                        await page.wait_for_timeout(1800)
                        logger.info("  ℹ️  Consent clicked")
                except:
                    pass

                # Wait for content to stabilize
                try:
                    await page.wait_for_load_state('networkidle', timeout=35000)
                except:
                    await page.wait_for_timeout(5000)

                item['url'] = page.url
                item['title'] = await page.title()

                content = ""

                # Modern selectors 2025–2026
                selectors = [
                    'article',
                    'main',
                    '[data-testid="article-body"], [data-testid="body"]',
                    'div[class*="RichText" i], .rich-text, [class*="article-body" i]',
                    'div[class*="content" i][class*="body" i]',
                    '[itemprop="articleBody"]',
                    'section[data-qa*="body" i], .story-body, .entry-content',
                ]

                for sel in selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            txt = await el.inner_text()
                            cleaned = ' '.join(txt.split())
                            if len(cleaned) > 400:
                                content = cleaned
                                break
                    except:
                        continue

                # Paragraph fallback
                if len(content) < 400:
                    try:
                        els = await page.query_selector_all('p, div[class*="para" i], div[class*="text" i], article div:not([class*="ad" i])')
                        texts = [ (await e.inner_text()).strip() async for e in els if (await e.inner_text()).strip() ]
                        texts = [t for t in texts if len(t) > 25]
                        if texts:
                            content = '\n\n'.join(texts)
                            content = ' '.join(content.split())
                    except:
                        pass

                # Clean body fallback
                if len(content) < 400:
                    try:
                        await page.evaluate('''() => {
                            document.querySelectorAll('nav, header, footer, aside, .ad, .banner, .popup, [role="dialog"], [id*="cookie"], .consent').forEach(e => e.remove());
                        }''')
                        body = await page.query_selector('body')
                        content = await body.inner_text()
                        content = ' '.join(content.split())
                    except:
                        pass

                content = content.strip()
                if len(content) >= 300:
                    item['status'] = 'success'
                    item['content'] = content
                    logger.info(f"  ✅ Playwright: {item['title'][:55]}... ({len(content):,} chars)")
                else:
                    item['error'] = f"Content too short ({len(content)} chars)"

            except Exception as e:
                item['error'] = str(e)
                logger.warning(f"  ❌ Playwright error: {e}")

            finally:
                await page.close()
                await context.close()
                await browser.close()

    except Exception as e:
        item['error'] = str(e)

    return item


def _scrape_with_trafilatura(url: str) -> Dict:
    item = {"url": url, "title": None, "content": "", "status": "failed", "error": None}
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 ... Chrome/130'}, timeout=18, allow_redirects=True)
        r.raise_for_status()
        content = trafilatura.extract(r.text)
        meta = trafilatura.extract_metadata(r.text)
        if content and len(content) >= 300:
            item.update({
                'status': 'success',
                'content': content.strip(),
                'title': meta.title if meta else None
            })
    except Exception as e:
        item['error'] = str(e)
    return item


def _scrape_with_beautifulsoup(url: str) -> Dict:
    item = {"url": url, "title": None, "content": "", "status": "failed", "error": None}
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 ...'}, timeout=15)
        soup = BeautifulSoup(r.content, 'html.parser')
        title = (soup.find('h1') or soup.find('title') or {}).get_text(' ', strip=True) or 'No title'

        for bad in soup(['script','style','nav','footer','header','aside','iframe']):
            bad.decompose()

        body = soup.find('article') or soup.find('main') or soup.body
        paras = body.find_all(['p','div']) if body else []
        content = '\n\n'.join(t.strip() for t in (p.get_text(' ', strip=True) for p in paras) if len(t) > 40)
        content = ' '.join(content.split())

        if len(content) >= 300:
            item.update(status='success', title=title, content=content)
    except Exception as e:
        item['error'] = str(e)
    return item


async def scrape_urls(urls: List[str], use_playwright: bool = True) -> List[Dict]:
    if use_playwright and PLAYWRIGHT_AVAILABLE:
        return [await scrape_url(u, True) for u in urls]     # sequential
    else:
        return await asyncio.gather(*(scrape_url(u, False) for u in urls))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_urls = ["https://www.bbc.com/news/technology"]
    results = asyncio.run(scrape_urls(test_urls, use_playwright=True))
    for r in results:
        print(f"\n{r['url']}\nStatus: {r['status']}\nTitle: {r.get('title')}\nLen: {len(r.get('content',''))}")