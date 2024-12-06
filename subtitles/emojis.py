import os
import random
import numpy as np

from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip


def add_animated_emojis(
    video_path,
    emojis_timestamps,
    output_path=None,
    emoji_dir="./emojis",
    vertical_position=600,
    relative_size=0.15,
    min_duration_for_animation=1.0,
    animation_params={
        'bounce_amplitude': 20,
        'wiggle_amplitude': 30,
        'circle_radius': 20,
        'figure8_x_amplitude': 30,
        'figure8_y_amplitude': 15,
        'zoom_amplitude': 0.15,
        'zoom_frequency': 3
    }
):
    """
    Add animated emoji overlays to video based on timestamps

    Parameters:
    - video_path: path to input video
    - emojis_timestamps: list of tuples (emoji_char, start_time)
    - output_path: path for output video (optional)
    - emoji_dir: directory containing emoji PNG files
    - vertical_position: fixed Y position for emojis
    - relative_size: emoji height relative to video height (0-1)
    - min_duration_for_animation: minimum duration for animated emojis
    - animation_params: dictionary of animation parameters
    """
    if output_path is None:
        output_path = video_path.replace('.mp4', '_with_emojis.mp4')

    video = VideoFileClip(video_path)
    duration = video.duration
    emoji_clips = []

    def get_animation(clip, center_x):
        """Internal function to generate random animation"""
        animations = [
            # Bounce
            {
                'position': lambda t: (center_x, vertical_position + np.sin(t * 2 * np.pi) * animation_params['bounce_amplitude']),
                'scale': lambda t: 1.0
            },

            # Wiggle
            {
                'position': lambda t: (center_x + np.sin(t * 3 * np.pi) * animation_params['wiggle_amplitude'], vertical_position),
                'scale': lambda t: 1.0
            },

            # Circle
            {
                'position': lambda t: (
                    center_x + np.cos(t * 2 * np.pi) * animation_params['circle_radius'],
                    vertical_position + np.sin(t * 2 * np.pi) * animation_params['circle_radius']
                ),
                'scale': lambda t: 1.0
            },

            # Figure 8
            {
                'position': lambda t: (
                    center_x + np.sin(t * 2 * np.pi) * animation_params['figure8_x_amplitude'],
                    vertical_position + np.sin(t * 4 * np.pi) * animation_params['figure8_y_amplitude']
                ),
                'scale': lambda t: 1.0
            },

            # Zoom pulse
            {
                'position': lambda t: (
                    center_x - (clip.w * (1 + np.sin(t * animation_params['zoom_frequency'] * np.pi) * animation_params['zoom_amplitude']) - clip.w) / 2,
                    vertical_position - (clip.h * (1 + np.sin(t * animation_params['zoom_frequency'] * np.pi) * animation_params['zoom_amplitude']) - clip.h) / 2
                ),
                'scale': lambda t: 1 + np.sin(t * animation_params['zoom_frequency'] * np.pi) * animation_params['zoom_amplitude']
            }
        ]

        return random.choice(animations)

    for i, (emoji_char, start_time) in enumerate(emojis_timestamps):
        end_time = duration if i == len(emojis_timestamps) - 1 else emojis_timestamps[i + 1][1]
        display_duration = end_time - start_time

        try:
            unicode_name = f"U{hex(ord(emoji_char))[2:].upper()}"
        except TypeError:
            unicode_name = f"U{hex(ord(emoji_char[0]))[2:].upper()}"

        emoji_path = os.path.join(emoji_dir, f"{unicode_name}.png")

        if os.path.exists(emoji_path):
            emoji_img = ImageClip(emoji_path)
            target_height = int(video.h * relative_size)
            emoji_img = emoji_img.resize(height=target_height)

            center_x = (video.w - emoji_img.w) // 2

            if display_duration >= min_duration_for_animation:
                animation = get_animation(emoji_img, center_x)
                emoji_img = (emoji_img
                    .set_position(animation['position'])
                    .resize(animation['scale'])
                    .set_start(start_time)
                    .set_end(end_time))
            else:
                position = lambda t: (center_x, vertical_position)
                emoji_img = emoji_img.set_position(position).set_start(start_time).set_end(end_time)

            emoji_clips.append(emoji_img)

    final_video = CompositeVideoClip([video] + emoji_clips)
    final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')

    final_video.close()
    video.close()

    return True
