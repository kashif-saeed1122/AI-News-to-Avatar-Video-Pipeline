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

# Voice Configuration - Choose male or female
# Get voice ID from .env or use default male voice
DEFAULT_VOICE_ID = os.environ.get('HEYGEN_VOICE_ID', '2d5b0e6cf36349c0b48b282c8e2ff88b')  # Male voice

# Common HeyGen Voice IDs:
VOICES = {
    # Male Voices
    'male_professional': '2d5b0e6cf36349c0b48b282c8e2ff88b',  # Professional male
    'male_casual': 'baf1c52778f0421585788312c4425a0e',        # Casual male
    'male_news': '40104aff703f4760bc2452535e0f9644',          # News anchor male
    
    # Female Voices
    'female_professional': '1bd001e7e50f421d891986aad5158bc8',  # Professional female
    'female_casual': 'e7dd8cf4292f4c3b9e4c4c5e3f6c1e77',       # Casual female
    'female_news': 'af90abcf592b4e0e9d252eb5b5c0c3d5',         # News anchor female
}


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
                raise RuntimeError(f"No video_id in response: {job_data}")
            
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
            
            raise TimeoutError(f"Video generation timed out after {max_wait}s")
            
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HeyGen API error: {e.response.status_code} - {e.response.text}")


def build_did_payload(
    script_text: str, 
    model: Optional[str] = 'expressive',
    voice: Optional[str] = 'male_professional',
    **kwargs
) -> dict:
    """
    Build HeyGen payload with customizable voice.
    
    Args:
        script_text: The news script text
        model: Not used (kept for compatibility)
        voice: Voice type - 'male_professional', 'male_news', 'female_professional', etc.
               Or provide a direct voice_id
    
    Returns:
        HeyGen API payload
    """
    avatar_id = kwargs.get('avatar_id', AVATAR_ID)
    
    # Get voice ID
    if voice in VOICES:
        voice_id = VOICES[voice]
    elif voice and len(voice) == 32:  # Direct voice ID provided
        voice_id = voice
    else:
        voice_id = DEFAULT_VOICE_ID  # Use default from .env or male_professional
    
    # HeyGen payload structure
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
                    "input_text": script_text,
                    "voice_id": voice_id
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
    
    logger.info(f"🎤 Using voice: {voice} (ID: {voice_id})")
    
    return payload


# Test function
async def test_voices():
    """Test different voices"""
    script = "Breaking news: Artificial intelligence adoption has increased by 40 percent."
    
    print("🎤 Testing Male Professional Voice...")
    payload = build_did_payload(script, voice='male_professional')
    
    try:
        result = await generate_video(payload)
        print(f"✅ Video URL: {result['video_url']}")
        print(f"🎉 Open in browser to watch!")
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_voices())