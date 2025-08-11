import PySimpleGUI as sg
import pandas as pd
import os
import json
from datetime import datetime
import threading
import time
from youtube_api import YouTubeSearcher
from csv_handler import CSVHandler
from config_manager import ConfigManager
from utils import format_duration, parse_duration_minutes, validate_api_key

class YouTubeFinderGUI:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.csv_handler = CSVHandler()
        self.youtube_searcher = None
        self.search_thread = None
        self.stop_search = False
        
        # Initialize API key
        api_key = os.getenv('YOUTUBE_API_KEY', '')
        if not api_key:
            sg.popup_error('YouTube API Key not found!\nPlease set YOUTUBE_API_KEY environment variable.')
            return
        
        if not validate_api_key(api_key):
            sg.popup_error('Invalid YouTube API Key format!\nPlease check your YOUTUBE_API_KEY environment variable.')
            return
            
        self.youtube_searcher = YouTubeSearcher(api_key)
        
        # UI State
        self.results_df = pd.DataFrame()
        self.quota_used = 0
        self.search_stats = {'scanned': 0, 'kept': 0, 'skipped': 0}
        
        # Create directories
        os.makedirs('data', exist_ok=True)
        os.makedirs('export', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        sg.theme('Default1')
        self.window = self.create_window()
        
    def create_window(self):
        # Duration options
        duration_options = ['Any', 'Short (<4 min)', 'Medium (4-20 min)', 'Long (>20 min)', 'Custom']
        
        # Region and language options (subset)
        region_options = ['', 'US', 'GB', 'CA', 'AU', 'DE', 'FR', 'JP', 'IN', 'BR']
        language_options = ['', 'en', 'es', 'fr', 'de', 'ja', 'pt', 'hi', 'ru', 'ko']
        
        # Left column - Controls
        controls_column = [
            [sg.Text('Keywords/Phrases (one per line):', font=('Arial', 10, 'bold'))],
            [sg.Multiline('', key='-KEYWORDS-', size=(30, 8))],
            
            [sg.Text('Duration:', font=('Arial', 10, 'bold'))],
            [sg.Combo(duration_options, default_value='Any', key='-DURATION-', 
                     enable_events=True, readonly=True, size=(25, 1))],
            [sg.Text('Min (minutes):'), sg.Input('', key='-DURATION_MIN-', size=(8, 1), disabled=True),
             sg.Text('Max:'), sg.Input('', key='-DURATION_MAX-', size=(8, 1), disabled=True)],
            
            [sg.Text('Views:', font=('Arial', 10, 'bold'))],
            [sg.Text('Min:'), sg.Input('', key='-VIEWS_MIN-', size=(12, 1)),
             sg.Text('Max:'), sg.Input('', key='-VIEWS_MAX-', size=(12, 1))],
            
            [sg.Text('Subscribers:', font=('Arial', 10, 'bold'))],
            [sg.Text('Min:'), sg.Input('', key='-SUBS_MIN-', size=(12, 1)),
             sg.Text('Max:'), sg.Input('', key='-SUBS_MAX-', size=(12, 1))],
            
            [sg.Text('Region:'), sg.Combo(region_options, key='-REGION-', size=(10, 1)),
             sg.Text('Language:'), sg.Combo(language_options, key='-LANGUAGE-', size=(10, 1))],
            
            [sg.Text('Pages per keyword:'), sg.Input('2', key='-PAGES-', size=(5, 1)),
             sg.Text('Daily API cap:'), sg.Input('9500', key='-API_CAP-', size=(8, 1))],
            
            [sg.Checkbox('Skip hidden subscriber counts', key='-SKIP_HIDDEN-', default=True),
             sg.Checkbox('Fresh search (clear history)', key='-FRESH_SEARCH-', default=False)],
            
            [sg.Button('Start Now', key='-START-', button_color=('white', 'green')),
             sg.Button('Save Schedule...', key='-SCHEDULE-'),
             sg.Button('Stop Search', key='-STOP-', disabled=True, button_color=('white', 'red'))]
        ]
        
        # Right column - Status and Results
        status_column = [
            [sg.Text('Status:', font=('Arial', 10, 'bold'))],
            [sg.Text('Estimated quota for this run: 0', key='-QUOTA_EST-')],
            [sg.Text('Current quota used: 0', key='-QUOTA_USED-')],
            [sg.ProgressBar(100, orientation='h', size=(40, 20), key='-PROGRESS-')],
            [sg.Text('Scanned: 0', key='-SCANNED-'), sg.Text('Kept: 0', key='-KEPT-'), 
             sg.Text('Skipped: 0', key='-SKIPPED-')],
            [sg.Text('')],  # Spacer
            
            [sg.Text('Results:', font=('Arial', 10, 'bold'))],
            [sg.Text('Filter by title:'), sg.Input('', key='-FILTER_TITLE-', enable_events=True, size=(20, 1)),
             sg.Text('Min views:'), sg.Input('', key='-FILTER_VIEWS-', enable_events=True, size=(10, 1))],
            
            # Results table
            [sg.Table(values=[], headings=['Title', 'Channel', 'Views', 'Duration', 'Published', 'Keyword'],
                     key='-RESULTS_TABLE-', max_col_width=50, auto_size_columns=False,
                     col_widths=[30, 20, 10, 8, 12, 15], num_rows=15, 
                     enable_events=True, select_mode=sg.TABLE_SELECT_MODE_BROWSE,
                     expand_x=True, expand_y=True)],
            
            [sg.Button('Open Video', key='-OPEN_VIDEO-', disabled=True),
             sg.Button('Open Channel', key='-OPEN_CHANNEL-', disabled=True),
             sg.Button('Export Results', key='-EXPORT-', disabled=True)]
        ]
        
        layout = [
            [sg.Column(controls_column, vertical_alignment='top', expand_y=True),
             sg.VSeparator(),
             sg.Column(status_column, vertical_alignment='top', expand_x=True, expand_y=True)]
        ]
        
        window = sg.Window('YouTube Finder', layout, size=(1200, 700), resizable=True, finalize=True)
        
        # Bind events for real-time filtering
        window['-FILTER_TITLE-'].bind('<KeyRelease>', '-FILTER_TITLE-')
        window['-FILTER_VIEWS-'].bind('<KeyRelease>', '-FILTER_VIEWS-')
        
        return window
    
    def estimate_quota(self, keywords, pages_per_keyword):
        """Estimate quota usage for the search"""
        try:
            keyword_count = len([k.strip() for k in keywords.split('\n') if k.strip()])
            if keyword_count == 0:
                return 0
            
            # search.list: 100 units per call
            search_calls = keyword_count * int(pages_per_keyword)
            search_quota = search_calls * 100
            
            # Estimate results (conservative: 30 results per page)
            estimated_results = search_calls * 30
            
            # videos.list: 1 unit per call (batches of 50)
            video_calls = (estimated_results + 49) // 50
            video_quota = video_calls * 1
            
            # channels.list: 1 unit per call (batches of 50)  
            channel_calls = video_calls  # Same batching
            channel_quota = channel_calls * 1
            
            total_quota = search_quota + video_quota + channel_quota
            return total_quota
            
        except Exception:
            return 0
    
    def update_results_table(self, filter_title='', filter_views=''):
        """Update the results table with current data and filters"""
        if self.results_df.empty:
            self.window['-RESULTS_TABLE-'].update(values=[])
            return
        
        # Apply filters
        filtered_df = self.results_df.copy()
        
        if filter_title:
            filtered_df = filtered_df[filtered_df['title'].str.contains(filter_title, case=False, na=False)]
        
        if filter_views and filter_views.isdigit():
            min_views = int(filter_views)
            filtered_df = filtered_df[filtered_df['view_count'] >= min_views]
        
        # Prepare table data
        table_data = []
        for _, row in filtered_df.iterrows():
            table_data.append([
                row['title'][:50] + '...' if len(row['title']) > 50 else row['title'],
                row['channel_title'],
                f"{int(row['view_count']):,}",
                format_duration(row['duration_minutes']),
                row['published_at'][:10],  # Just date part
                row['keyword']
            ])
        
        self.window['-RESULTS_TABLE-'].update(values=table_data)
    
    def start_search(self):
        """Start the YouTube search in a separate thread"""
        self.stop_search = False
        self.search_stats = {'scanned': 0, 'kept': 0, 'skipped': 0}
        
        # Get search parameters
        keywords_text = self.window['-KEYWORDS-'].get().strip()
        if not keywords_text:
            sg.popup_error('Please enter at least one keyword!')
            return
        
        keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        
        try:
            pages_per_keyword = int(self.window['-PAGES-'].get() or '2')
            api_cap = int(self.window['-API_CAP-'].get() or '9500')
        except ValueError:
            sg.popup_error('Pages per keyword and API cap must be valid numbers!')
            return
        
        # Validate quota
        estimated_quota = self.estimate_quota(keywords_text, pages_per_keyword)
        if estimated_quota > api_cap:
            sg.popup_error(f'Estimated quota ({estimated_quota}) exceeds your daily cap ({api_cap})!\n'
                          'Reduce keywords or pages per keyword.')
            return
        
        # Get filters
        duration_filter = self.window['-DURATION-'].get()
        duration_min = self.window['-DURATION_MIN-'].get()
        duration_max = self.window['-DURATION_MAX-'].get()
        
        views_min = self.window['-VIEWS_MIN-'].get()
        views_max = self.window['-VIEWS_MAX-'].get()
        subs_min = self.window['-SUBS_MIN-'].get()
        subs_max = self.window['-SUBS_MAX-'].get()
        
        region = self.window['-REGION-'].get()
        language = self.window['-LANGUAGE-'].get()
        
        skip_hidden = self.window['-SKIP_HIDDEN-'].get()
        fresh_search = self.window['-FRESH_SEARCH-'].get()
        
        # Prepare search config
        search_config = {
            'keywords': keywords,
            'pages_per_keyword': pages_per_keyword,
            'api_cap': api_cap,
            'duration_filter': duration_filter,
            'duration_min': duration_min,
            'duration_max': duration_max,
            'views_min': views_min,
            'views_max': views_max,
            'subs_min': subs_min,
            'subs_max': subs_max,
            'region': region,
            'language': language,
            'skip_hidden': skip_hidden,
            'fresh_search': fresh_search
        }
        
        # Update UI state
        self.window['-START-'].update(disabled=True)
        self.window['-STOP-'].update(disabled=False)
        self.window['-PROGRESS-'].update(0)
        
        # Start search thread
        self.search_thread = threading.Thread(target=self.search_worker, args=(search_config,))
        self.search_thread.daemon = True
        self.search_thread.start()
    
    def search_worker(self, config):
        """Worker thread for YouTube search"""
        try:
            # Clear history if fresh search
            if config['fresh_search']:
                self.csv_handler.clear_history()
            
            # Initialize results
            all_results = []
            self.quota_used = 0
            total_keywords = len(config['keywords'])
            
            for i, keyword in enumerate(config['keywords']):
                if self.stop_search:
                    break
                
                # Update progress
                progress = int((i / total_keywords) * 100)
                self.window.write_event_value('-UPDATE_PROGRESS-', progress)
                self.window.write_event_value('-UPDATE_STATUS-', f'Searching: {keyword}')
                
                try:
                    # Search videos for this keyword
                    videos = self.youtube_searcher.search_videos(
                        query=keyword,
                        max_pages=config['pages_per_keyword'],
                        region=config['region'],
                        language=config['language'],
                        duration_filter=config['duration_filter'],
                        quota_limit=config['api_cap'] - self.quota_used
                    )
                    
                    self.quota_used += self.youtube_searcher.quota_used
                    
                    # Apply filters and deduplication
                    for video in videos:
                        if self.stop_search:
                            break
                        
                        self.search_stats['scanned'] += 1
                        
                        # Check if already seen
                        if self.csv_handler.is_video_seen(video['video_id']):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        # Apply duration filter
                        duration_minutes = parse_duration_minutes(video.get('duration', ''))
                        if not self.passes_duration_filter(duration_minutes, config):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        # Apply view filter
                        view_count = int(video.get('view_count', 0))
                        if not self.passes_view_filter(view_count, config):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        # Apply subscriber filter
                        subscriber_count = int(video.get('subscriber_count', 0))
                        if config['skip_hidden'] and video.get('hidden_subscriber_count', False):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        if not self.passes_subscriber_filter(subscriber_count, config):
                            self.search_stats['skipped'] += 1
                            continue
                        
                        # Add keyword to video data
                        video['keyword'] = keyword
                        video['duration_minutes'] = duration_minutes
                        all_results.append(video)
                        self.search_stats['kept'] += 1
                        
                        # Update stats display
                        self.window.write_event_value('-UPDATE_STATS-', self.search_stats.copy())
                    
                    # Check quota limit
                    if self.quota_used >= config['api_cap']:
                        self.window.write_event_value('-UPDATE_STATUS-', 'Daily quota limit reached!')
                        break
                        
                except Exception as e:
                    self.window.write_event_value('-UPDATE_STATUS-', f'Error searching {keyword}: {str(e)}')
                    continue
            
            # Save results
            if all_results and not self.stop_search:
                results_df = pd.DataFrame(all_results)
                today = datetime.now().strftime('%Y-%m-%d')
                results_file = f'export/results_{today}.csv'
                
                self.csv_handler.save_results(results_df, results_file)
                self.csv_handler.update_history([r['video_id'] for r in all_results])
                
                # Update UI with results
                self.results_df = results_df
                self.window.write_event_value('-SEARCH_COMPLETE-', len(all_results))
            
            else:
                self.window.write_event_value('-SEARCH_COMPLETE-', 0)
                
        except Exception as e:
            self.window.write_event_value('-SEARCH_ERROR-', str(e))
    
    def passes_duration_filter(self, duration_minutes, config):
        """Check if video passes duration filter"""
        if config['duration_filter'] == 'Any':
            return True
        elif config['duration_filter'] == 'Short (<4 min)':
            return duration_minutes < 4
        elif config['duration_filter'] == 'Medium (4-20 min)':
            return 4 <= duration_minutes <= 20
        elif config['duration_filter'] == 'Long (>20 min)':
            return duration_minutes > 20
        elif config['duration_filter'] == 'Custom':
            min_dur = float(config['duration_min']) if config['duration_min'] else 0
            max_dur = float(config['duration_max']) if config['duration_max'] else float('inf')
            return min_dur <= duration_minutes <= max_dur
        return True
    
    def passes_view_filter(self, view_count, config):
        """Check if video passes view count filter"""
        if config['views_min'] and view_count < int(config['views_min']):
            return False
        if config['views_max'] and view_count > int(config['views_max']):
            return False
        return True
    
    def passes_subscriber_filter(self, subscriber_count, config):
        """Check if video passes subscriber count filter"""
        if config['subs_min'] and subscriber_count < int(config['subs_min']):
            return False
        if config['subs_max'] and subscriber_count > int(config['subs_max']):
            return False
        return True
    
    def stop_search_thread(self):
        """Stop the current search"""
        self.stop_search = True
        if self.search_thread and self.search_thread.is_alive():
            self.search_thread.join(timeout=2)
        
        # Reset UI
        self.window['-START-'].update(disabled=False)
        self.window['-STOP-'].update(disabled=True)
        self.window['-PROGRESS-'].update(0)
    
    def save_schedule(self):
        """Save current settings for scheduled runs"""
        settings = self.get_current_settings()
        
        try:
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            
            sg.popup('Settings saved successfully!\n\n'
                    'To schedule this search:\n'
                    '1. Run schedule_helper.bat as Administrator\n'
                    '2. Or manually create a Windows Task Scheduler job to run:\n'
                    '   python app_headless.py --settings settings.json',
                    title='Schedule Saved')
                    
        except Exception as e:
            sg.popup_error(f'Failed to save settings: {str(e)}')
    
    def get_current_settings(self):
        """Get current UI settings as dictionary"""
        return {
            'keywords': self.window['-KEYWORDS-'].get(),
            'duration': self.window['-DURATION-'].get(),
            'duration_min': self.window['-DURATION_MIN-'].get(),
            'duration_max': self.window['-DURATION_MAX-'].get(),
            'views_min': self.window['-VIEWS_MIN-'].get(),
            'views_max': self.window['-VIEWS_MAX-'].get(),
            'subs_min': self.window['-SUBS_MIN-'].get(),
            'subs_max': self.window['-SUBS_MAX-'].get(),
            'region': self.window['-REGION-'].get(),
            'language': self.window['-LANGUAGE-'].get(),
            'pages': self.window['-PAGES-'].get(),
            'api_cap': self.window['-API_CAP-'].get(),
            'skip_hidden': self.window['-SKIP_HIDDEN-'].get(),
            'fresh_search': self.window['-FRESH_SEARCH-'].get()
        }
    
    def run(self):
        """Main event loop"""
        while True:
            event, values = self.window.read(timeout=100)
            
            if event == sg.WIN_CLOSED:
                break
            
            # Handle events
            if event == '-DURATION-':
                # Enable/disable custom duration inputs
                is_custom = values['-DURATION-'] == 'Custom'
                self.window['-DURATION_MIN-'].update(disabled=not is_custom)
                self.window['-DURATION_MAX-'].update(disabled=not is_custom)
            
            elif event == '-START-':
                self.start_search()
            
            elif event == '-STOP-':
                self.stop_search_thread()
            
            elif event == '-SCHEDULE-':
                self.save_schedule()
            
            elif event in ['-FILTER_TITLE-', '-FILTER_VIEWS-']:
                self.update_results_table(
                    values['-FILTER_TITLE-'],
                    values['-FILTER_VIEWS-']
                )
            
            elif event == '-RESULTS_TABLE-':
                # Enable buttons when row is selected
                selected = len(values['-RESULTS_TABLE-']) > 0
                self.window['-OPEN_VIDEO-'].update(disabled=not selected)
                self.window['-OPEN_CHANNEL-'].update(disabled=not selected)
            
            elif event == '-OPEN_VIDEO-':
                self.open_selected_video()
            
            elif event == '-OPEN_CHANNEL-':
                self.open_selected_channel()
            
            elif event == '-EXPORT-':
                self.export_results()
            
            # Handle thread events
            elif event == '-UPDATE_PROGRESS-':
                self.window['-PROGRESS-'].update(values[event])
            
            elif event == '-UPDATE_STATUS-':
                pass  # Could add status text field
            
            elif event == '-UPDATE_STATS-':
                stats = values[event]
                self.window['-SCANNED-'].update(f"Scanned: {stats['scanned']}")
                self.window['-KEPT-'].update(f"Kept: {stats['kept']}")
                self.window['-SKIPPED-'].update(f"Skipped: {stats['skipped']}")
                self.window['-QUOTA_USED-'].update(f"Current quota used: {self.quota_used}")
            
            elif event == '-SEARCH_COMPLETE-':
                result_count = values[event]
                self.stop_search_thread()
                
                if result_count > 0:
                    sg.popup(f'Search completed!\nFound {result_count} videos.')
                    self.update_results_table()
                    self.window['-EXPORT-'].update(disabled=False)
                else:
                    sg.popup('Search completed but no videos found matching your criteria.')
            
            elif event == '-SEARCH_ERROR-':
                error_msg = values[event]
                self.stop_search_thread()
                sg.popup_error(f'Search failed: {error_msg}')
            
            # Update quota estimate on input changes
            if event in ['-KEYWORDS-', '-PAGES-']:
                keywords_text = values['-KEYWORDS-']
                pages = values['-PAGES-']
                if keywords_text and pages:
                    estimated = self.estimate_quota(keywords_text, pages)
                    self.window['-QUOTA_EST-'].update(f'Estimated quota for this run: {estimated}')
        
        self.window.close()
    
    def open_selected_video(self):
        """Open selected video in browser"""
        try:
            selected_rows = self.window['-RESULTS_TABLE-'].get()
            if not selected_rows:
                return
            
            row_index = self.window['-RESULTS_TABLE-'].SelectedRows[0]
            video_url = self.results_df.iloc[row_index]['video_url']
            
            import webbrowser
            webbrowser.open(video_url)
            
        except Exception as e:
            sg.popup_error(f'Failed to open video: {str(e)}')
    
    def open_selected_channel(self):
        """Open selected channel in browser"""
        try:
            selected_rows = self.window['-RESULTS_TABLE-'].get()
            if not selected_rows:
                return
            
            row_index = self.window['-RESULTS_TABLE-'].SelectedRows[0]
            channel_id = self.results_df.iloc[row_index]['channel_id']
            channel_url = f'https://www.youtube.com/channel/{channel_id}'
            
            import webbrowser
            webbrowser.open(channel_url)
            
        except Exception as e:
            sg.popup_error(f'Failed to open channel: {str(e)}')
    
    def export_results(self):
        """Export current results to CSV"""
        if self.results_df.empty:
            sg.popup('No results to export!')
            return
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'export/manual_export_{timestamp}.csv'
            
            self.csv_handler.save_results(self.results_df, filename)
            sg.popup(f'Results exported to:\n{filename}')
            
        except Exception as e:
            sg.popup_error(f'Failed to export results: {str(e)}')

def main():
    app = YouTubeFinderGUI()
    if app.youtube_searcher:  # Only run if API key is valid
        app.run()

if __name__ == '__main__':
    main()
