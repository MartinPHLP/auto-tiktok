import os

from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate


load_dotenv()

class SubtitleFormat(BaseModel):
    subtitles_segments: List[str] = Field(description="The segments of the voiceover")
    segment_smiley: List[str] = Field(description="The smiley for each segment. One smiley for each segment.")

model = ChatAnthropic(model='claude-3-5-sonnet-20241022')
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant that formats subtitles for a video.
     You take the voiceover of a tiktok video and format it into a list of segments with a matching smiley for each segment.
     Each segment should be a short sentence that is easy to read and understand, not too long (max 10 words).
     The smiley should be the most appropriate smiley for the segment.
     The goal is to make the video more engaging and interesting for the viewer.
     """),
    ("user", "VOICEOVER: {voiceover}"),
])

chain = prompt | model.with_structured_output(SubtitleFormat)

def format_subtitles(voiceover: str, retries: int = 3) -> SubtitleFormat:
    for attempt in range(retries):
        try:
            result = chain.invoke({"voiceover": voiceover})
            return result

        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")

            if attempt == retries - 1:
                raise

            else:
                print("Retrying...")


if __name__ == "__main__":
    print(format_subtitles("Ever suddenly JERK awake feeling like you're falling? It's called a hypnic jerk - your brain literally thinks you're dying! As your muscles relax for sleep, your brain panics and jolts you awake!"))
