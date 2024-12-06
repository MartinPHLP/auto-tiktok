from moviepy.editor import VideoFileClip, CompositeVideoClip
from .text_drawer import (
    get_text_size_ex,
    create_text_ex,
    blur_text_clip,
    Word,
)


lines_cache = {}
shadow_cache = {}

def calculate_lines(text, font, font_size, stroke_width, frame_width):
    global lines_cache

    arg_hash = hash((text, font, font_size, stroke_width, frame_width))

    if arg_hash in lines_cache:
        return lines_cache[arg_hash]

    lines = []

    line_to_draw = None
    line = ""
    words = text.split()
    word_index = 0
    total_height = 0
    while word_index < len(words):
        word = words[word_index]
        line += word + " "
        text_size = get_text_size_ex(line.strip(), font, font_size, stroke_width)
        text_width = text_size[0]
        line_height = text_size[1]

        if text_width < frame_width:
            line_to_draw = {
                "text": line.strip(),
                "height": line_height,
            }
            word_index += 1
        else:
            if not line_to_draw:
                print(f"NOTICE: Word '{line.strip()}' is too long for the frame!")
                line_to_draw = {
                    "text": line.strip(),
                    "height": line_height,
                }
                word_index += 1

            lines.append(line_to_draw)
            total_height += line_height
            line_to_draw = None
            line = ""

    if line_to_draw:
        lines.append(line_to_draw)
        total_height += line_height

    data = {
        "lines": lines,
        "height": total_height,
    }

    lines_cache[arg_hash] = data

    return data

def create_shadow(text: str, font_size: int, font: str, blur_radius: float, opacity: float=1.0):
    global shadow_cache

    arg_hash = hash((text, font_size, font, blur_radius, opacity))

    if arg_hash in shadow_cache:
        return shadow_cache[arg_hash].copy()

    shadow = create_text_ex(text, font_size, "black", font, opacity=opacity)
    shadow = blur_text_clip(shadow, int(font_size*blur_radius))

    shadow_cache[arg_hash] = shadow.copy()

    return shadow

def write_subtitles(font, font_size, stroke_width, stroke_color, shadow_blur, font_color, word_highlight_color, padding, highlight_current_word, increase_font_size, captions, tmp_tiktok, final_output, vertical_position_offset=0):
    # Open the video file
    video = VideoFileClip(tmp_tiktok)
    text_bbox_width = video.w-padding*2
    clips = [video]

    for caption in captions:
        captions_to_draw = []
        if highlight_current_word:
            for i, word in enumerate(caption["words"]):
                if i + 1 < len(caption["words"]):
                    end = caption["words"][i+1]["start_time"]
                else:
                    end = word["end_time"]

                captions_to_draw.append({
                    "text": caption["segment"],
                    "start": word["start_time"],
                    "end": end,
                })
        else:
            captions_to_draw.append(caption)

        for current_index, caption in enumerate(captions_to_draw):
            line_data = calculate_lines(caption["text"], font, font_size, stroke_width, text_bbox_width)

            text_y_offset = video.h // 2 - line_data["height"] // 2 + vertical_position_offset
            index = 0
            for line in line_data["lines"]:
                pos = ("center", text_y_offset)

                words = line["text"].split()
                word_list = []
                for w in words:
                    word_obj = Word(w)
                    if highlight_current_word and index == current_index:
                        word_obj.set_color(word_highlight_color)
                        word_obj.set_size(font_size + int(font_size * increase_font_size))
                    index += 1
                    word_list.append(word_obj)

                # Create shadow
                shadow_left = 1.0
                while shadow_left >= 1:
                    shadow_left -= 1
                    shadow = create_shadow(line["text"], font_size, font, shadow_blur, opacity=1)
                    shadow = shadow.set_start(caption["start"])
                    shadow = shadow.set_duration(caption["end"] - caption["start"])
                    shadow = shadow.set_position(pos)
                    clips.append(shadow)

                if shadow_left > 0:
                    shadow = create_shadow(line["text"], font_size, font, shadow_blur, opacity=shadow_left)
                    shadow = shadow.set_start(caption["start"])
                    shadow = shadow.set_duration(caption["end"] - caption["start"])
                    shadow = shadow.set_position(pos)
                    clips.append(shadow)

                # Create text
                text = create_text_ex(word_list, font_size, font_color, font, stroke_color=stroke_color, stroke_width=stroke_width)
                text = text.set_start(caption["start"])
                text = text.set_duration(caption["end"] - caption["start"])
                text = text.set_position(pos)
                clips.append(text)

                text_y_offset += line["height"]


    video_with_text = CompositeVideoClip(clips)

    video_with_text.write_videofile(
        filename=final_output,
        codec="libx264",
        fps=video.fps
    )
