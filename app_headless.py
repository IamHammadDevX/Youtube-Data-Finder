import argparse
import json
import os
import sys
from datetime import datetime
import pandas as pd
from youtube_api import YouTubeSearcher
from csv_handler import CSVHandler
from utils import parse_duration_minutes, validate_api_key

class HeadlessYouTubeSearcher:
    def __init__(self, settings_file):
        # Load settings
        with open(settings_file, 'r') as f:
            self.settings = json.load(f)
        
        # Initialize components
        self.csv_handler = CSVHandler()
        
        # Initialize API
        api_key = os.getenv('YOUTUBE_API_KEY', '')
        if not api_key:
            print('ERROR: YouTube API Key not found! Please set YOUTUBE_API_KEY environment variable.')
            sys.exit(1)
        
        if not validate_api_key(api_key):
            print('ERROR: Invalid YouTube API Key format!')
            sys.exit(1)
            
        self.youtube_searcher = YouTubeSearcher(api_key)
        
        # Initialize state
        self.quota_used = 0
        self.search_stats = {'scanned': 0, 'kept': 0, 'skipped': 0}
        
        # Create directories
        os.makedirs('data', exist_ok=True)
        os.makedirs('export', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def run_search(self):
        """Execute the headless search"""
        start_time = datetime.now()
        print(f"Starting YouTube search at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Parse keywords
            keywords_text = self.settings.get('keywords', '').strip()
            if not keywords_text:
                print('ERROR: No keywords specified in settings!')
                return False
            
            keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
            print(f"Searching for {len(keywords)} keywords: {', '.join(keywords[:3])}{'...' if len(keywords) > 3 else ''}")
            
            # Get search parameters
            pages_per_keyword = int(self.settings.get('pages', 2))
            api_cap = int(self.settings.get('api_cap', 9500))
            
            # Clear history if fresh search
            if self.settings.get('fresh_search', False):
                print("Fresh search enabled - clearing history")
                self.csv_handler.clear_history()
            
            # Initialize results
            all_results = []
            
            for i, keyword in enumerate(keywords, 1):
                print(f"\nProcessing keyword {i}/{len(keywords)}: '{keyword}'")
                
                try:
                    # Search videos for this keyword
                    videos = self.youtube_searcher.search_videos(
                        query=keyword,
                        max_pages=pages_per_keyword,
                        region=self.settings.get('region', ''),
                        language=self.settings.get('language', ''),
                        duration_filter=self.settings.get('duration', 'Any'),
                        quota_limit=api_cap - self.quota_used
                    )
                    
                    self.quota_used += self.youtube_searcher.quota_used
                    print(f"  Found {len(videos)} videos, quota used so far: {self.quota_used}")
                    
                    # Apply filters and deduplication
                    keyword_results = []
                    for video in videos:
                        self.search_stats['scanned'] += 1
                        
                        # Check if already seen
                        if self.csv_handler.is_video_seen(video['video_id']):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        # Apply duration filter
                        duration_minutes = parse_duration_minutes(video.get('duration', ''))
                        if not self.passes_duration_filter(duration_minutes):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        # Apply view filter
                        view_count = int(video.get('view_count', 0))
                        if not self.passes_view_filter(view_count):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        # Apply subscriber filter
                        subscriber_count = int(video.get('subscriber_count', 0))
                        if self.settings.get('skip_hidden', True) and video.get('hidden_subscriber_count', False):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        if not self.passes_subscriber_filter(subscriber_count):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        # Add keyword and duration to video data
                        video['keyword'] = keyword
                        video['duration_minutes'] = duration_minutes
                        keyword_results.append(video)
                        self.search_stats['kept'] += 1
                    
                    all_results.extend(keyword_results)
                    print(f"  Kept {len(keyword_results)} videos after filtering")
                    
                    # Check quota limit
                    if self.quota_used >= api_cap:
                        print(f"\nDaily quota limit reached ({self.quota_used}/{api_cap})")
                        break
                        
                except Exception as e:
                    print(f"  ERROR searching '{keyword}': {str(e)}")
                    continue
            
            # Save results
            end_time = datetime.now()
            duration = end_time - start_time
            
            print(f"\nSearch completed in {duration}")
            print(f"Stats: Scanned {self.search_stats['scanned']}, Kept {self.search_stats['kept']}, Skipped {self.search_stats['skipped']}")
            print(f"Total quota used: {self.quota_used}")
            
            if all_results:
                results_df = pd.DataFrame(all_results)
                today = datetime.now().strftime('%Y-%m-%d')
                results_file = f'export/results_{today}.csv'
                
                self.csv_handler.save_results(results_df, results_file)
                self.csv_handler.update_history([r['video_id'] for r in all_results])
                
                print(f"Saved {len(all_results)} results to: {results_file}")
                
                # Log the run
                self.log_run(start_time, self.quota_used, len(keywords), len(all_results))
                
                return True
            else:
                print("No results found matching criteria")
                return False
                
        except Exception as e:
            print(f"FATAL ERROR: {str(e)}")
            return False
    
    def passes_duration_filter(self, duration_minutes):
        """Check if video passes duration filter"""
        duration_filter = self.settings.get('duration', 'Any')
        
        if duration_filter == 'Any':
            return True
        elif duration_filter == 'Short (<4 min)':
            return duration_minutes < 4
        elif duration_filter == 'Medium (4-20 min)':
            return 4 <= duration_minutes <= 20
        elif duration_filter == 'Long (>20 min)':
            return duration_minutes > 20
        elif duration_filter == 'Custom':
            duration_min = self.settings.get('duration_min', '')
            duration_max = self.settings.get('duration_max', '')
            min_dur = float(duration_min) if duration_min else 0
            max_dur = float(duration_max) if duration_max else float('inf')
            return min_dur <= duration_minutes <= max_dur
        return True
    
    def passes_view_filter(self, view_count):
        """Check if video passes view count filter"""
        views_min = self.settings.get('views_min', '')
        views_max = self.settings.get('views_max', '')
        
        if views_min and view_count < int(views_min):
            return False
        if views_max and view_count > int(views_max):
            return False
        return True
    
    def passes_subscriber_filter(self, subscriber_count):
        """Check if video passes subscriber count filter"""
        subs_min = self.settings.get('subs_min', '')
        subs_max = self.settings.get('subs_max', '')
        
        if subs_min and subscriber_count < int(subs_min):
            return False
        if subs_max and subscriber_count > int(subs_max):
            return False
        return True
    
    def log_run(self, start_time, quota_used, keywords_count, results_count):
        """Log the run details"""
        try:
            log_file = 'logs/runs.csv'
            log_data = {
                'run_timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'estimated_quota_used': quota_used,
                'keywords_count': keywords_count,
                'results_count': results_count
            }
            
            # Create or append to log file
            if os.path.exists(log_file):
                log_df = pd.read_csv(log_file)
                log_df = pd.concat([log_df, pd.DataFrame([log_data])], ignore_index=True)
            else:
                log_df = pd.DataFrame([log_data])
            
            log_df.to_csv(log_file, index=False)
            
        except Exception as e:
            print(f"Warning: Failed to log run details: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='YouTube Finder - Headless Mode')
    parser.add_argument('--settings', required=True, help='Path to settings JSON file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.settings):
        print(f'ERROR: Settings file not found: {args.settings}')
        sys.exit(1)
    
    searcher = HeadlessYouTubeSearcher(args.settings)
    success = searcher.run_search()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
