import requests
import time
from datetime import datetime
import isodate
from utils import parse_duration_minutes

class YouTubeSearcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://www.googleapis.com/youtube/v3'
        self.quota_used = 0
        self.rate_limit_delay = 0.1  # Small delay between requests
        
    def search_videos(self, query, max_pages=2, region='', language='',
                      duration_filter='Any', quota_limit=10000,
                      published_after='', published_before=''):
        """
        Search for videos using the YouTube API
        Returns list of video dictionaries with complete metadata
        Accepts optional RFC-3339 date strings 'published_after' and 'published_before'
        """
        all_videos = []
        page_token = None
        pages_fetched = 0
        self.quota_used = 0

        # Map duration filter to API parameter
        duration_param = self._get_duration_param(duration_filter)

        while pages_fetched < max_pages and (not quota_limit or self.quota_used < quota_limit):
            # Check if we have enough quota for this request
            if quota_limit and (self.quota_used + 100) > quota_limit:
                print(f"Quota limit would be exceeded, stopping search")
                break

            try:
                # Build search parameters
                params = {
                    'part': 'snippet',
                    'q': query,
                    'type': 'video',
                    'order': 'viewCount',
                    'maxResults': 50,
                    'key': self.api_key
                }

                if page_token:
                    params['pageToken'] = page_token
                if region:
                    params['regionCode'] = region
                if language:
                    params['relevanceLanguage'] = language
                if duration_param:
                    params['videoDuration'] = duration_param
                if published_after:
                    params['publishedAfter'] = published_after
                if published_before:
                    params['publishedBefore'] = published_before

                # Make search request
                response = requests.get(f'{self.base_url}/search', params=params)
                time.sleep(self.rate_limit_delay)

                if response.status_code != 200:
                    print(f"Search API error: {response.status_code} - {response.text}")
                    break

                data = response.json()
                self.quota_used += 100  # search.list costs 100 units

                if 'items' not in data or not data['items']:
                    break

                # Extract video IDs
                video_ids = [item['id']['videoId'] for item in data['items']]

                # Get detailed video information
                video_details = self._get_video_details(video_ids, quota_limit - self.quota_used)
                if not video_details:
                    break

                # Get channel information for subscriber counts
                channel_ids = list(set([video['channel_id'] for video in video_details]))
                channel_info = self._get_channel_details(channel_ids, quota_limit - self.quota_used)

                # Merge channel info with video details
                # Merge channel info with video details
                for video in video_details:
                    channel_data = channel_info.get(video['channel_id'], {})
                    video.update(channel_data)

                all_videos.extend(video_details)

                # Get next page token
                page_token = data.get('nextPageToken')
                if not page_token:
                    break

                pages_fetched += 1

            except requests.RequestException as e:
                print(f"Request error during search: {str(e)}")
                break
            except Exception as e:
                print(f"Unexpected error during search: {str(e)}")
                break

        return all_videos
    
    def _get_video_details(self, video_ids, quota_remaining):
        """Get detailed information for a list of video IDs"""
        if not video_ids or (quota_remaining and quota_remaining < 1):
            return []
        
        videos = []
        
        # Process in batches of 50 (API limit)
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            try:
                params = {
                    'part': 'statistics,contentDetails,snippet',
                    'id': ','.join(batch_ids),
                    'key': self.api_key
                }
                
                response = requests.get(f'{self.base_url}/videos', params=params)
                time.sleep(self.rate_limit_delay)
                
                if response.status_code != 200:
                    print(f"Videos API error: {response.status_code} - {response.text}")
                    continue
                
                data = response.json()
                self.quota_used += 1  # videos.list costs 1 unit
                
                for item in data.get('items', []):
                    video_data = self._parse_video_item(item)
                    if video_data:
                        videos.append(video_data)
                
                # Check quota
                if quota_remaining and self.quota_used >= quota_remaining:
                    break
                    
            except requests.RequestException as e:
                print(f"Request error getting video details: {str(e)}")
                continue
            except Exception as e:
                print(f"Unexpected error getting video details: {str(e)}")
                continue
        
        return videos
    
    def _get_channel_details(self, channel_ids, quota_remaining):
        """Get channel information for subscriber counts"""
        if not channel_ids or (quota_remaining and quota_remaining < 1):
            return {}
        
        channel_info = {}
        
        # Process in batches of 50
        for i in range(0, len(channel_ids), 50):
            batch_ids = channel_ids[i:i+50]
            
            try:
                params = {
                    'part': 'statistics',
                    'id': ','.join(batch_ids),
                    'key': self.api_key
                }
                
                response = requests.get(f'{self.base_url}/channels', params=params)
                time.sleep(self.rate_limit_delay)
                
                if response.status_code != 200:
                    print(f"Channels API error: {response.status_code} - {response.text}")
                    continue
                
                data = response.json()
                self.quota_used += 1  # channels.list costs 1 unit
                
                for item in data.get('items', []):
                    channel_id = item['id']
                    statistics = item.get('statistics', {})
                    
                    channel_info[channel_id] = {
                        'subscriber_count': int(statistics.get('subscriberCount', 0)),
                        'hidden_subscriber_count': statistics.get('hiddenSubscriberCount', False)
                    }
                
                # Check quota
                if quota_remaining and self.quota_used >= quota_remaining:
                    break
                    
            except requests.RequestException as e:
                print(f"Request error getting channel details: {str(e)}")
                continue
            except Exception as e:
                print(f"Unexpected error getting channel details: {str(e)}")
                continue
        
        return channel_info
    
    def _parse_video_item(self, item):
        """Parse a video item from the API response"""
        try:
            video_id = item['id']
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            
            # Parse duration
            duration_iso = content_details.get('duration', 'PT0S')
            try:
                duration = isodate.parse_duration(duration_iso)
                duration_minutes = duration.total_seconds() / 60
            except Exception:
                duration_minutes = 0
            
            video_data = {
                'video_id': video_id,
                'video_url': f'https://www.youtube.com/watch?v={video_id}',
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'tags': ','.join(snippet.get('tags', [])),
                'channel_title': snippet.get('channelTitle', ''),
                'channel_id': snippet.get('channelId', ''),
                'published_at': snippet.get('publishedAt', ''),
                'view_count': int(statistics.get('viewCount', 0)),
                'duration': duration_iso,
                'duration_minutes': duration_minutes
            }
            # NEW: keep subscriber data inside each video dict
            video_data['subscriber_count'] = 0  # will be overwritten later
            video_data['hidden_subscriber_count'] = False
                        
            return video_data
            
        except Exception as e:
            print(f"Error parsing video item: {str(e)}")
            return None
    
    def _get_duration_param(self, duration_filter):
        """Convert duration filter to API parameter"""
        if duration_filter == 'Short (<4 min)':
            return 'short'
        elif duration_filter == 'Medium (4-20 min)':
            return 'medium'
        elif duration_filter == 'Long (>20 min)':
            return 'long'
        else:
            return None  # 'Any' or 'Custom' - no API filter
