import os
import anthropic

from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

def generate_content(account_topic):
   client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

   # Generate topic
   topic = client.messages.create(
       model="claude-3-5-sonnet-20241022",
       max_tokens=1024,
       messages=[{
           "role": "user",
           "content": f"""You are a topic writer for a tiktok video. You write the topic only, not the text or the script of the video.
                        Write the topic for the following account : {account_topic}.
                        Give the topic, only the topic, not the whole script.
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
                        << {account_topic} >>
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
                        Short Script (30 words max):
                        """
       }]
   )

   return script.content[0].text

def create_tts(text, voice="fable", output_path='output.mp3'):
    """Create Text-to-Speech using OpenAI's API"""
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Get full path in tmp directory
        tmp_path = os.path.join("./tmp", output_path)

        # Generate speech
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )

        # Save to file
        response.stream_to_file(tmp_path)

    except Exception as e:
        print(f"Error generating TTS: {str(e)}")
        raise
