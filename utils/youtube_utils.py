import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()


def get_youtube_stats(url):
    """
    输入 YouTube URL，返回真实的粉丝数和频道标题
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or "youtube.com" not in url.lower():
        return 0, ""

    try:
        youtube = build("youtube", "v3", developerKey=api_key)

        # 1. 尝试直接从搜索中获取频道 ID
        # 这种方式最通用，能处理 @handle, /c/ 各种格式
        search_res = youtube.search().list(
            q=url,
            type="channel",
            part="id,snippet",
            maxResults=1
        ).execute()

        if not search_res.get('items'):
            return 0, ""

        channel_id = search_res['items'][0]['id']['channelId']
        channel_name = search_res['items'][0]['snippet']['title']

        # 2. 获取该频道的详细统计数据
        detail_res = youtube.channels().list(
            id=channel_id,
            part="statistics"
        ).execute()

        if not detail_res.get('items'):
            return 0, channel_name

        stats = detail_res['items'][0]['statistics']
        subscriber_count = int(stats.get('subscriberCount', 0))

        return subscriber_count, channel_name
    except Exception as e:
        print(f"⚠️ YouTube API 访问受限或出错: {e}")
        return 0, ""