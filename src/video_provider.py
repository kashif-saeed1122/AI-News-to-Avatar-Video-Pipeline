import os
import httpx
import asyncio
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# HeyGen Configuration
HEYGEN_API_KEY = os.environ.get('HEYGEN_API_KEY', 'sk_V2_hgu_kaBycQjfHtU_rdIaOx4ctdlgz4np1eJChU4ZsP2Jtr0c')
HEYGEN_GENERATE_URL = 'https://api.heygen.com/v2/video/generate'
HEYGEN_STATUS_URL = 'https://api.heygen.com/v1/video_status.get'

# Your avatar ID
AVATAR_ID = os.environ.get('HEYGEN_AVATAR_ID', '967948d61edc46c8854d639ea170aab9')


async def generate_video(payload: dict, max_wait: int = 300) -> dict:
    """Generate video using HeyGen API."""
    if not HEYGEN_API_KEY:
        raise RuntimeError('HEYGEN_API_KEY must be set')

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": HEYGEN_API_KEY
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            logger.info("🎬 Creating HeyGen video...")
            
            # Create video
            resp = await client.post(HEYGEN_GENERATE_URL, json=payload, headers=headers)
            resp.raise_for_status()
            job_data = resp.json()
            
            video_id = job_data.get('data', {}).get('video_id')
            if not video_id:
                raise RuntimeError(f"No video_id: {job_data}")
            
            logger.info(f"✅ Video job created: {video_id}")
            
            # Poll for completion
            elapsed = 0
            poll_interval = 10
            
            while elapsed < max_wait:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                
                status_resp = await client.get(
                    HEYGEN_STATUS_URL,
                    params={'video_id': video_id},
                    headers=headers
                )
                status_resp.raise_for_status()
                status_data = status_resp.json()
                
                status = status_data.get('data', {}).get('status')
                logger.info(f"⏳ Status: {status} ({elapsed}s)")
                
                if status == 'completed':
                    video_url = status_data.get('data', {}).get('video_url')
                    logger.info(f"✅ Video ready: {video_url}")
                    return {
                        'id': video_id,
                        'status': 'done',
                        'result_url': video_url,
                        'video_url': video_url,
                        'duration': status_data.get('data', {}).get('duration', 0),
                        'provider': 'heygen'
                    }
                elif status == 'failed':
                    raise RuntimeError(f"Video failed: {status_data.get('data', {}).get('error')}")
            
            raise TimeoutError(f"Timed out after {max_wait}s")
            
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HeyGen API error: {e.response.status_code} - {e.response.text}")


def build_did_payload(script_text: str, model: Optional[str] = 'expressive', **kwargs) -> dict:
    """
    Build HeyGen payload - EXACTLY as HeyGen API expects it.
    """
    avatar_id = kwargs.get('avatar_id', AVATAR_ID)
    
    # THIS IS THE CORRECT PAYLOAD STRUCTURE
    payload = {
        "caption": False,
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "text",
                    "input_text": script_text,  # ← YOUR SCRIPT GOES HERE
                    "voice_id": "f38a635bee7a4d1f9b0a654a31d050d2"
                },
                "background": {
                    "type": "color",
                    "value": "#FFFFFF"
                }
            }
        ],
        "dimension": {
            "width": 1280,
            "height": 720
        }
    }
    
    return payload


# QUICK TEST
async def test():
    script = "Breaking news: AI adoption has increased by 40 percent in the past year."
    payload = build_did_payload(script)
    
    print("Testing HeyGen...")
    print(f"Script: {script}")
    
    result = await generate_video(payload)
    print(f"✅ Video URL: {result['video_url']}")
    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test())