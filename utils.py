import requests
import io
import re
import os
import shutil
import random
import pandas as pd
import yt_dlp
from PIL import ImageFont
from openai import OpenAI
import anthropic



def download_google_font(config):
    """Download and load Google Font"""
    try:
        # Get CSS
        font_url = config['font']['google_font']['url']
        css_response = requests.get(font_url)
        css_content = css_response.text

        # Extract font file URL using a more robust pattern
        font_url_match = re.search(r'https://[^)]+\.ttf', css_content)
        if font_url_match:
            font_url = font_url_match.group(0)

            # Download font file
            font_response = requests.get(font_url)
            font_bytes = io.BytesIO(font_response.content)

            # Return the font bytes
            return font_bytes
    except Exception as e:
        print(f"Failed to load Google Font: {e}")
        return None

def get_font(config, size):
    """Get font with improved Google Fonts support"""
    # Try Google Font first
    if 'google_font' in config['font']:
        font_bytes = download_google_font(config)
        if font_bytes is not None:
            try:
                return ImageFont.truetype(font_bytes, size=size)
            except Exception as e:
                print(f"Error loading Google Font: {e}")

    # Fallback to local fonts
    for font_path in config['font']['fallback_paths']:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            continue

    print("Warning: No suitable font found, using default bitmap font")
    return ImageFont.load_default()

def cleanup_tmp():
    """Clean up temporary directory"""
    tmp_dir = "./tmp"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)


def get_random_video(urls_csv='urls.csv', output_path='video.mp4'):
   df = pd.read_csv(urls_csv)
   url = random.choice(df['url'].tolist())

   try:
       ydl_opts = {
           'format': 'best[ext=mp4]',
           'outtmpl': output_path,
           'quiet': True,
           'no_warnings': True,
       }

       with yt_dlp.YoutubeDL(ydl_opts) as ydl:
           print(f"Downloading video from: {url}")
           ydl.download([url])
           return True

   except Exception as e:
       raise Exception(f"Failed to download video: {str(e)}")


def generate_content():
   client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

   # Generate topic
   topic = client.messages.create(
       model="claude-3-5-sonnet-20241022",
       max_tokens=1024,
       messages=[{
           "role": "user",
           "content": """You are a topic writer for a tiktok video. You write the topic only, not the text of the video.
Write the topic for the following account : Daily "did you know" for adults.
Give the topic, only the topic.
Topic:"""
       }]
   )

   # Generate script
   script = client.messages.create(
       model="claude-3-5-sonnet-20241022",
       max_tokens=1024,
       messages=[{
           "role": "user",
           "content": f"""You are a TikTok script writer.
The TikTok account for which you generate text has the following theme:
<< Daily "did you know" for adults >>
Write the voice-over script from the following topic:
{topic.content[0].text}
Remember this is for TikTok - you need to:
- Hook viewers in first 3 seconds
- Use short, punchy sentences
- Keep energy high and dynamic
- Use conversational language
- Build curiosity and suspense
- Never drag or over-explain
- Maintain fast pacing
- No emojis or hashtags (it's a voiceover)
Give only the script, without introduction.
Short Script (30 words max):"""
       }]
   )

   return script.content[0].text

def create_tts(text, output_path='output.mp3'):
    """Create Text-to-Speech using OpenAI's API"""
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Get full path in tmp directory
        tmp_path = os.path.join("./tmp", output_path)

        # Generate speech
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",  # You can change to "echo", "fable", "onyx", "nova", or "shimmer"
            input=text
        )

        # Save to file
        response.stream_to_file(tmp_path)

    except Exception as e:
        print(f"Error generating TTS: {str(e)}")
        raise
