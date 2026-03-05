import os
from google import genai
from google.genai import types

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    return genai.Client(api_key=api_key)

def categorize_channels(channels_info):
    """
    channels_info: list of dict with 'title', 'description'
    Returns categories for each channel.
    """
    client = get_gemini_client()
    
    prompt = "다음 채널 목록을 보고 각 채널을 적절한 계층적 카테고리(예: IT/Tech > AI, 라이프스타일 > 요리 등)로 분류해주세요.\n\n"
    for i, ch in enumerate(channels_info):
        prompt += f"채널명: {ch['title']}\n설명: {ch['description'][:200]}...\n\n"
    prompt += "결과는 JSON 리스트 형식으로 반환해 주세요. 형식: [{\"channel_title\": \"...\", \"category\": \"...\"}]"
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return response.text

def summarize_videos(videos_info):
    """
    videos_info: list of dict with 'title', 'description'
    Returns a unified summary of the recent videos.
    """
    client = get_gemini_client()
    
    prompt = "다음은 특정 구독 채널의 최근 1주일간 영상들입니다. 이 영상들의 주요 내용을 분석하여 전체적인 채널의 최신 트렌드와 핵심 내용을 3~4문장으로 요약해주세요.\n\n"
    for v in videos_info:
        prompt += f"제목: {v['title']}\n설명: {v['description'][:200]}...\n\n"
        
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
        )
    )
    return response.text
