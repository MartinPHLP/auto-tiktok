import os
import anthropic
import time
import pandas as pd
import random
from gtts import gTTS
import yt_dlp
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, ImageSequenceClip
from dotenv import load_dotenv
import ssl
import certifi
from groq import Groq, APITimeoutError
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import shutil
import requests
import io
import re
from openai import OpenAI
from utils import get_font, cleanup_tmp, get_random_video, generate_content, create_tts
from format_subtitles import format_subtitles
load_dotenv()

# Add at the top of the file with other configurations
SUBTITLE_CONFIG = {
    # Font settings
    'font': {
        'google_font': {
            'family': 'Albert Sans',  # Une police moderne et lisible
            'variant': '800',     # Semi-bold
            'url': 'https://fonts.googleapis.com/css2?family=Albert+Sans:wght@800&display=swap'
        },
        'fallback_paths': [
            'arial.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            'C:/Windows/Fonts/arial.ttf',
        ],
        'size_ratio': 0.045,     # Légèrement plus petit pour plus d'élégance
    },

    # Text style
    'text': {
        'primary_color': '#00FF00',  # Bright green color
        'outline': {
            'color': 'black',
            'width': 10,              # Increased outline width for larger borders
            'enabled': True
        },
        'shadow': {
            'enabled': False,
        }
    },

    # Position and layout
    'layout': {
        'vertical_position': 0.85,    # Position from top (0-1)
        'max_width_ratio': 0.85,      # Maximum width relative to video width
        'line_spacing': 1.6,          # Space between lines (relative to font size)
        'margin_bottom': 50,          # Pixels from bottom
        'center_align': True          # Center align text
    },

    # Animation
    'animation': {
        'fade_duration': 0.5,         # Seconds for fade in/out
        'word_timing': {
            'enabled': True,          # Enable word-by-word timing
            'min_words': 1,           # Minimum words to show at start
            'smoothing': 0.2          # Smoothing factor for word timing
        }
    }
}

def wrap_text(text, font, max_width):
    """Split text into lines that fit within max_width"""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        # Try adding the next word
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line.append(word)
        else:
            # If current line has words, add it to lines
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # If single word is too long, force it on its own line
                lines.append(word)
                current_line = []

    # Add the last line if there are remaining words
    if current_line:
        lines.append(' '.join(current_line))

    return lines

def add_text(draw, frame_pil, text, x, y, font, config):
    """Render text without background"""
    if frame_pil.mode != 'RGBA':
        frame_pil = frame_pil.convert('RGBA')

    # Calculate maximum width
    max_width = int(frame_pil.width * config['layout']['max_width_ratio'])
    lines = wrap_text(text, font, max_width)

    # Calculate total height
    line_spacing = config['layout']['line_spacing']
    line_height = font.getbbox("Aj")[3]
    total_height = line_height * line_spacing * len(lines)

    # Adjust starting position
    y = y - (total_height / 2)

    # Process each line
    for line in lines:
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]

        # Center text horizontally
        line_x = (frame_pil.width - text_width) / 2 if config['layout']['center_align'] else x

        # Draw main text
        draw.text(
            (line_x, y),
            line,
            font=font,
            fill=config['text']['primary_color']
        )

        # Move to next line
        y += line_height * line_spacing

    return frame_pil

def transcribe_audio(audio_path):
    """Transcribe audio using OpenAI's Whisper API with word-level timestamps"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )

            return transcription

    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        raise

def create_tiktok(video_path, audio_path, output_path='tiktok.mp4'):
    # Load clips
    audio_voiceover = AudioFileClip(audio_path)
    video = VideoFileClip(video_path)
    original_audio = video.audio
    theme_audio = AudioFileClip('./theme.mp3')

    # Get random start time for theme music
    max_start = max(0, theme_audio.duration - audio_voiceover.duration)
    random_start = random.uniform(0, max_start)

    # Cut theme music to match voiceover duration and set volume to 50%
    theme_audio = theme_audio.subclip(random_start, random_start + audio_voiceover.duration)
    theme_audio = theme_audio.volumex(0.07)

    # Trim video and original audio to match voiceover length
    video = video.subclip(0, audio_voiceover.duration)
    original_audio = original_audio.subclip(0, audio_voiceover.duration)

    original_audio = original_audio.volumex(0.5)

    # Combine all audio tracks
    final_audio = CompositeAudioClip([original_audio, theme_audio, audio_voiceover])

    # Calculate target dimensions for 9:16 aspect ratio
    target_width = 1080
    target_height = 1920

    # Resize video to cover the target height while maintaining aspect ratio
    height_ratio = target_height / video.h
    video = video.resize(height=target_height)

    # Center crop to target width
    x_center = video.w / 2
    video = video.crop(x1=x_center - target_width/2,
                      y1=0,
                      x2=x_center + target_width/2,
                      y2=target_height)

    # Set the final audio
    final_video = video.set_audio(final_audio)
    final_video.write_videofile(output_path, codec='libx264',
                              audio_codec='aac')

def add_subtitles(video_path, audio_path, output_path='subtitled_video.mp4', config=SUBTITLE_CONFIG):
    print("  ⌛ Transcribing audio...")
    transcription = transcribe_audio(audio_path)
    formatted_subtitles = format_subtitles(transcription.text)
    print(formatted_subtitles)
    print("  ✓ Audio transcribed")

    print("  ⌛ Loading video...")
    video = VideoFileClip(video_path)
    frames_dir = os.path.join("./tmp", "frames")
    os.makedirs(frames_dir, exist_ok=True)

    fps = video.fps
    duration = video.duration
    frame_count = int(fps * duration)

    print(f"  ⌛ Processing {frame_count} frames...")
    for i, frame_num in enumerate(range(frame_count)):
        if i % int(frame_count/10) == 0:
            progress = (i / frame_count) * 100
            print(f"    Progress: {progress:.1f}%")

        current_time = frame_num / fps

        # Get frame first (moved outside the if condition)
        frame = video.get_frame(current_time)
        frame_pil = Image.fromarray(frame).convert('RGBA')
        draw = ImageDraw.Draw(frame_pil)

        # Find current words based on timestamp
        current_words = []
        for word in transcription.words:
            if float(word.start) <= current_time <= float(word.end):
                current_words.append(word.word)

        current_text = " ".join(current_words)

        # Add text only if there's text to display
        if current_text:
            # Configure font
            font_size = int(frame.shape[1] * config['font']['size_ratio'])
            font = get_font(config, font_size)

            # Add text without background
            x = (frame.shape[1] - font.getbbox(current_text)[2]) / 2
            y = frame.shape[0] * config['layout']['vertical_position']
            frame_pil = add_text(draw, frame_pil, current_text, x, y, font, config)

        # Convert and save frame (moved outside the if condition)
        frame = np.array(frame_pil.convert('RGB'))
        cv2.imwrite(os.path.join(frames_dir, f"frame_{frame_num:06d}.jpg"),
                   cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    print("  ⌛ Combining frames into final video...")
    frames = ImageSequenceClip(frames_dir, fps=fps)
    final_video = frames.set_audio(video.audio)
    final_video.write_videofile(output_path, codec='libx264',
                              audio_codec='aac',
                              logger=None)

    shutil.rmtree(frames_dir)
    print("  ✓ Video rendering complete")

def main():
    try:
        print("\n=== Starting TikTok Video Generation ===\n")

        # Initialize/clean tmp directory
        print("🧹 Cleaning temporary directory...")
        cleanup_tmp()

        # Generate content
        print("\n📝 Generating content...")
        script_text = generate_content()
        # script_text = "This is a test, now you can watch the video. And you can see the subtitles. Ok, bye."
        print(f"✓ Generated script: \"{script_text}\"\n")

        # Create TTS
        print("🎤 Creating text-to-speech audio...")
        create_tts(script_text, 'tts.mp3')
        print("✓ Audio generated successfully\n")

        # Update paths
        tmp_gameplay = "./gameplay.mp4"
        tmp_tts = os.path.join("./tmp", "tts.mp3")
        tmp_tiktok = os.path.join("./tmp", "temp_tiktok.mp4")
        final_output = "final_tiktok.mp4"

        # Create TikTok
        print("🎬 Creating base TikTok video...")
        create_tiktok(tmp_gameplay, tmp_tts, tmp_tiktok)
        print("✓ Base video created successfully\n")

        # Add subtitles
        print("💬 Adding subtitles...")
        add_subtitles(tmp_tiktok, tmp_tts, final_output)
        print("✓ Subtitles added successfully\n")

        print(f"✨ Final video generated: {final_output}\n")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        print("🧹 Cleaning up temporary files...")
        cleanup_tmp()
        print("\n=== Process Complete ===\n")

if __name__ == "__main__":
    main()
