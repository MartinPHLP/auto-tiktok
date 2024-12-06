import os
from dotenv import load_dotenv
from subtitles import write_subtitles, format_subtitles, add_animated_emojis
from ft_create_content import generate_content, create_tts
from ft_utils import (
    cleanup_tmp,
    get_random_video,
    transcribe_audio,
    get_segment_timestamps,
    create_tiktok,
)

load_dotenv()


PATHS = {
    "tmp_dir": "./tmp",
    "fonts_dir": "./subtitles/fonts",
    "outputs_dir": "./results",
    "urls_csv": "./content_srcs/urls.csv",
    "music_path": "./content_srcs/theme.mp3",
}

CONFIG = {
    "general": {
        "account_topic": "Daily 'did you know' for adults",
        "voice": "echo",
        "original_audio_volume": 0.1,
        "music_volume": 0.1,
        "global_blur": 0.0,
    },
    "subtitles": {
        "font": os.path.join(PATHS[
            "fonts_dir"
        ],
        "Bangers-Regular.ttf"),
        "font_size": 130,
        "stroke_width": 8,
        "stroke_color": "black",
        "shadow_blur": 0.3,
        "font_color": "white",
        "vertical_position_offset": 150,
        "word_highlight_color": "red",
        "padding": 50,
        "highlight_current_word": True,
        "increase_font_size": 0.1,
        "emojis": {
            "vertical_position": 700,
            "relative_size": 0.15,
            "min_duration_for_animation": 1.0,
        }
    }
}

def main():
    try:
        print("\n=== Starting TikTok Video Generation ===\n")

        # Generate content
        print("\n📝 Generating content...")
        script_text = generate_content(CONFIG["general"]["account_topic"])
        print(f"✓ Generated script: \"{script_text}\"\n")

        # Create TTS
        print("🎤 Creating text-to-speech audio...")
        create_tts(script_text, CONFIG["general"]["voice"], 'tts.mp3')
        print("✓ Audio generated successfully\n")

        # Update paths
        tmp_gameplay = os.path.join(PATHS["tmp_dir"], "gameplay.mp4")
        tmp_tts = os.path.join(PATHS["tmp_dir"], "tts.mp3")
        tmp_tiktok = os.path.join(PATHS["tmp_dir"], "temp_tiktok.mp4")
        final_output = os.path.join(PATHS["outputs_dir"], "final_tiktok.mp4")

        # Create TikTok
        print("🎬 Creating base TikTok video...")
        # get_random_video(PATHS["urls_csv"], output_path=tmp_gameplay)
        create_tiktok(
            video_path=tmp_gameplay,
            audio_path=tmp_tts,
            music_path=PATHS["music_path"],
            music_volume=CONFIG["general"]["music_volume"],
            original_audio_volume=CONFIG["general"]["original_audio_volume"],
            global_blur=CONFIG["general"]["global_blur"],
            output_path=tmp_tiktok
        )
        print("✓ Base video created successfully\n")

        transcription = transcribe_audio(tmp_tts)
        subtitle_format = format_subtitles(transcription)
        smileys = subtitle_format.segment_smiley

        # print("\n\n\n")
        # print(f"SUBTITLES:\n{subtitle_format}\n")
        # print("\n\n\n")

        captions = get_segment_timestamps(transcription, subtitle_format)

        smileys_timestamps = [(smiley, caption["start_time"]) for smiley, caption in zip(smileys, captions)]
        print(f"SMILEY_TIMESTAMPS:\n{smileys_timestamps}\n")

        # Add emojis to video
        add_animated_emojis(
            video_path=tmp_tiktok,
            emojis_timestamps=smileys_timestamps,
            output_path=tmp_tiktok,
            **CONFIG["subtitles"]["emojis"]
        )

        write_subtitles(
            font=CONFIG["subtitles"]["font"],
            font_size=CONFIG["subtitles"]["font_size"],
            stroke_width=CONFIG["subtitles"]["stroke_width"],
            stroke_color=CONFIG["subtitles"]["stroke_color"],
            shadow_blur=CONFIG["subtitles"]["shadow_blur"],
            font_color=CONFIG["subtitles"]["font_color"],
            word_highlight_color=CONFIG["subtitles"]["word_highlight_color"],
            padding=CONFIG["subtitles"]["padding"],
            highlight_current_word=CONFIG["subtitles"]["highlight_current_word"],
            increase_font_size=CONFIG["subtitles"]["increase_font_size"],
            vertical_position_offset=CONFIG["subtitles"]["vertical_position_offset"],
            captions=captions,
            tmp_tiktok=tmp_tiktok,
            final_output=final_output,
        )


        print(f"✨ Final video generated: {final_output}\n")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        print("🧹 Cleaning up temporary files...")
        # cleanup_tmp()
        print("\n=== Process Complete ===\n")

if __name__ == "__main__":
    main()
