import os
import shutil
import random
import yt_dlp

import pandas as pd
from openai import OpenAI
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
from PIL import Image, ImageFilter
import numpy as np


def cleanup_tmp():
    """Clean up temporary directory"""
    tmp_dir = "./tmp"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)

def get_random_video(urls_csv, output_path='video.mp4'):
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

def get_segment_timestamps(transcription, subtitle_format):
    """
    Extract timestamps and words for each subtitle segment

    Args:
        transcription: Whisper API transcription response with word-level timestamps
        subtitle_format: SubtitleFormat object containing subtitle segments

    Returns:
        List of dicts containing:
        - segment: str (the subtitle text)
        - start_time: float (segment start time)
        - end_time: float (segment end time)
        - words: list of dicts with word-level timing info
    """
    segments_info = []
    current_pos = 0
    full_text = transcription.text.lower()

    # Accéder à la liste des segments de sous-titres
    subtitles_segments = subtitle_format.subtitles_segments

    for segment in subtitles_segments:
        normalized_segment = segment.lower().strip('?!.,')
        segment_pos = full_text.find(normalized_segment, current_pos)

        if segment_pos == -1:
            first_words = ' '.join(normalized_segment.split()[:3])
            segment_pos = full_text.find(first_words, current_pos)

        if segment_pos != -1:
            text_before = full_text[:segment_pos]
            words_before = len(text_before.split())

            # Get all words that belong to this segment
            segment_words = []
            word_count = len(normalized_segment.split())

            if words_before < len(transcription.words):
                start_time = transcription.words[words_before].start

                # Collect words and their timing info
                for i in range(words_before, min(words_before + word_count, len(transcription.words))):
                    word_info = transcription.words[i]
                    segment_words.append({
                        "word": word_info.word,
                        "start_time": word_info.start,
                        "end_time": word_info.end
                    })

                # Calculate end time from last word
                end_time = segment_words[-1]["end_time"] if segment_words else start_time

                segments_info.append({
                    "segment": segment,
                    "start_time": start_time,
                    "end_time": end_time,
                    "words": segment_words,
                })

                current_pos = segment_pos + len(normalized_segment)

    return segments_info

def create_tiktok(video_path, audio_path, music_path, music_volume=0.07, original_audio_volume=0.5, global_blur=0.0, output_path='tiktok.mp4'):
    # Load clips
    audio_voiceover = AudioFileClip(audio_path)
    video = VideoFileClip(video_path)
    original_audio = video.audio
    music = AudioFileClip(music_path)

    # Get random start time for theme music
    max_start = max(0, music.duration - audio_voiceover.duration)
    random_start = random.uniform(0, max_start)

    # Cut theme music to match voiceover duration and set volume to 50%
    music = music.subclip(random_start, random_start + audio_voiceover.duration)
    music = music.volumex(music_volume)

    # Trim video and original audio to match voiceover length
    video = video.subclip(0, audio_voiceover.duration)
    original_audio = original_audio.subclip(0, audio_voiceover.duration)

    original_audio = original_audio.volumex(original_audio_volume)

    # Combine all audio tracks
    final_audio = CompositeAudioClip([original_audio, music, audio_voiceover])

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

    # Appliquer le flou si global_blur > 0
    if global_blur > 0:
        # Convertir global_blur (0-1) en radius (1-20)
        blur_radius = int(1 + (global_blur * 19))  # Map 0.0-1.0 to 1-20

        def blur_frame(get_frame, t):
            img = Image.fromarray(get_frame(t))
            img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            return np.array(img)

        video = video.fl(blur_frame)

    # Set the final audio
    final_video = video.set_audio(final_audio)
    final_video.write_videofile(output_path, codec='libx264',
                              audio_codec='aac')
