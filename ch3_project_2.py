# Project 2：Youtube视频摘要
# 视频选用：The Thinking Game | Full documentary | Tribeca Film Festival official selection
# 视频链接：https://www.youtube.com/watch?v=d95J8yzvjbQ

import os
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

def get_transcript(video_id: str) -> list:
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id)
    
    return transcript

def list_to_txt(transcript_list) -> list:
    text = []
    for snippet in transcript_list.snippets:
        text.append(snippet.text)
    
    return text

def save_list_to_txt(text: list, filename: str) -> None:
    text1 = text[0:int(1/4*len(text))]
    text2 = text[int(1/4*len(text)):int(2/4*len(text))]
    text3 = text[int(2/4*len(text)):int(3/4*len(text))]
    text4 = text[int(3/4*len(text)):]
    text = [text1, text2, text3, text4]
    for i, t in enumerate(text):
        with open(filename+f"_{i}.txt", "w") as f:
            for s in t:
                f.write(s)
                f.write("\n")
    
def text_to_summary(filename: str) -> str:
    with open(filename, "r") as f:
        transcript = f.read()
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    # 调用ChatCompletion端点，并使用gpt-3.5-turbo模型
    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Summarize the following text"},
            {"role": "assistant", "content": "Yes."},
            {"role": "user", "content": transcript},
        ],
    )
    return response.choices[0].message.content

def main():
    video_id = "d95J8yzvjbQ"
    transcript_list = get_transcript(video_id)
    text = list_to_txt(transcript_list)
    save_list_to_txt(text, "transcript")
    transcript_0 = text_to_summary("transcript_0.txt")
    transcript_1 = text_to_summary("transcript_1.txt")
    transcript_2 = text_to_summary("transcript_2.txt")
    transcript_3 = text_to_summary("transcript_3.txt")
    transcript_total = transcript_0 + transcript_1 + transcript_2 + transcript_3
    with open("transcript.txt", "w") as f:
        f.write(transcript_total)
    
    transcript = text_to_summary("transcript.txt")
    with open("summary.txt", "w") as f:
        f.write(transcript)

if __name__ == '__main__':
    main()
