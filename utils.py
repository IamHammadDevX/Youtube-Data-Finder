import re
import isodate
from datetime import datetime, timedelta

def format_duration(minutes):
    """Format duration in minutes to human readable format"""
    try:
        minutes = float(minutes)
        if minutes < 1:
            return f"{int(minutes * 60)}s"
        elif minutes < 60:
            return f"{int(minutes)}m"
        else:
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
    except (ValueError, TypeError):
        return "Unknown"

def parse_duration_minutes(duration_iso):
    """Convert ISO 8601 duration to minutes"""
    try:
        if not duration_iso or duration_iso == 'PT0S':
            return 0
        
        # Parse using isodate library
        duration = isodate.parse_duration(duration_iso)
        return duration.total_seconds() / 60
        
    except Exception:
        # Fallback manual parsing for simple cases
        try:
            # Match patterns like PT1H30M45S, PT5M30S, PT45S
            pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
            match = re.match(pattern, duration_iso)
            
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                
                total_minutes = hours * 60 + minutes + seconds / 60
                return total_minutes
            
        except Exception:
            pass
        
        return 0

def validate_api_key(api_key):
    """Basic validation of YouTube API key format"""
    if not api_key:
        return False
    
    # YouTube API keys are typically 39 characters long and contain alphanumeric characters and hyphens/underscores
    if len(api_key) < 30 or len(api_key) > 50:
        return False
    
    # Check if it contains only valid characters
    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        return False
    
    return True

def format_number(number):
    """Format numbers with commas for thousands"""
    try:
        return f"{int(number):,}"
    except (ValueError, TypeError):
        return str(number)

def parse_date(date_string):
    """Parse various date formats"""
    try:
        # Try ISO format first (YouTube API format)
        if 'T' in date_string:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        
        # Try other common formats
        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        return datetime.now()  # Fallback
        
    except Exception:
        return datetime.now()

def get_relative_date(date_obj):
    """Get relative date description (e.g., '2 days ago')"""
    try:
        if isinstance(date_obj, str):
            date_obj = parse_date(date_obj)
        
        now = datetime.now()
        if date_obj.tzinfo:
            # Handle timezone-aware datetime
            now = now.replace(tzinfo=date_obj.tzinfo)
        
        delta = now - date_obj
        
        if delta.days == 0:
            if delta.seconds < 3600:
                minutes = delta.seconds // 60
                return f"{minutes} minutes ago" if minutes > 1 else "1 minute ago"
            else:
                hours = delta.seconds // 3600
                return f"{hours} hours ago" if hours > 1 else "1 hour ago"
        elif delta.days == 1:
            return "1 day ago"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} weeks ago" if weeks > 1 else "1 week ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} months ago" if months > 1 else "1 month ago"
        else:
            years = delta.days // 365
            return f"{years} years ago" if years > 1 else "1 year ago"
            
    except Exception:
        return "Unknown"

def clean_text_for_csv(text):
    """Clean text for safe CSV storage"""
    if not text:
        return ""
    
    # Replace problematic characters
    text = str(text)
    text = text.replace('\n', ' ')  # Replace newlines with spaces
    text = text.replace('\r', '')   # Remove carriage returns
    text = text.replace('\t', ' ')  # Replace tabs with spaces
    
    # Remove or replace other control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in ['\n'])
    
    return text.strip()

def estimate_search_quota(keywords_count, pages_per_keyword=2, videos_per_page=50):
    """Estimate quota usage for a search operation"""
    try:
        # search.list: 100 units per call
        search_calls = keywords_count * pages_per_keyword
        search_quota = search_calls * 100
        
        # Estimate number of videos found
        estimated_videos = search_calls * videos_per_page * 0.8  # Assume 80% success rate
        
        # videos.list: 1 unit per call (batches of 50)
        video_calls = max(1, int(estimated_videos / 50))
        video_quota = video_calls * 1
        
        # channels.list: 1 unit per call (batches of 50, same as videos)
        channel_quota = video_calls * 1
        
        total_quota = search_quota + video_quota + channel_quota
        
        return {
            'search_quota': search_quota,
            'video_quota': video_quota,
            'channel_quota': channel_quota,
            'total_quota': total_quota,
            'estimated_videos': int(estimated_videos)
        }
        
    except Exception:
        return {
            'search_quota': 0,
            'video_quota': 0,
            'channel_quota': 0,
            'total_quota': 0,
            'estimated_videos': 0
        }

def sanitize_filename(filename):
    """Sanitize filename for Windows compatibility"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename.strip()
