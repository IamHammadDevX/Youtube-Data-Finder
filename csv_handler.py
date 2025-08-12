import pandas as pd
import os
from datetime import datetime, timedelta

class CSVHandler:
    def __init__(self):
        self.history_file = 'data/seen_history.csv'
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        os.makedirs('data', exist_ok=True)
        os.makedirs('export', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
    
    def save_results(self, results_df, filename):
        """Save search results to CSV file, appending to existing data."""
        try:
            # Ensure all required columns are present
            required_columns = [
                'title', 'description', 'tags', 'video_url', 'video_id',
                'channel_title', 'channel_id', 'subscriber_count', 'view_count',
                'comments', 'likes', 'duration_minutes', 'published_at', 'keyword'
            ]
            
            # Add missing columns with default values
            for col in required_columns:
                if col not in results_df.columns:
                    results_df[col] = ''
            
            # Reorder columns to match specification
            results_df = results_df[required_columns]
            
            # Check if the file already exists
            if os.path.exists(filename):
                # Load existing data
                existing_df = pd.read_csv(filename)
                # Append new results to existing data
                combined_df = pd.concat([existing_df, results_df], ignore_index=True)
                # Save the combined data
                combined_df.to_csv(filename, index=False, encoding='utf-8-sig')
            else:
                # Save new results if the file does not exist
                results_df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            print(f"Results saved to: {filename}")
            
        except Exception as e:
            raise Exception(f"Failed to save results: {str(e)}")
    
    def load_history(self):
        """Load the seen video history"""
        try:
            if os.path.exists(self.history_file):
                history_df = pd.read_csv(self.history_file)
                return set(history_df['video_id'].tolist())
            else:
                return set()
        except Exception as e:
            print(f"Warning: Failed to load history: {str(e)}")
            return set()
    
    def is_video_seen(self, video_id):
        """Check if a video ID has been seen before"""
        try:
            if not os.path.exists(self.history_file):
                return False
            
            history_df = pd.read_csv(self.history_file)
            return video_id in history_df['video_id'].values
            
        except Exception as e:
            print(f"Warning: Failed to check video history: {str(e)}")
            return False
    
    def update_history(self, video_ids):
        """Add new video IDs to the history"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Create new history entries
            new_entries = pd.DataFrame({
                'video_id': video_ids,
                'first_seen_date': today
            })
            
            # Load existing history
            if os.path.exists(self.history_file):
                existing_history = pd.read_csv(self.history_file)
                # Remove duplicates (keep existing first_seen_date)
                new_entries = new_entries[~new_entries['video_id'].isin(existing_history['video_id'])]
                # Combine with existing
                updated_history = pd.concat([existing_history, new_entries], ignore_index=True)
            else:
                updated_history = new_entries
            
            # Save updated history
            updated_history.to_csv(self.history_file, index=False)
            print(f"Updated history with {len(new_entries)} new video IDs")
            
        except Exception as e:
            print(f"Warning: Failed to update history: {str(e)}")
    
    def clear_history(self):
        """Clear the video history (for fresh searches)"""
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
                print("History cleared for fresh search")
        except Exception as e:
            print(f"Warning: Failed to clear history: {str(e)}")
    
    def load_results(self, filename):
        """Load results from a CSV file"""
        try:
            if os.path.exists(filename):
                return pd.read_csv(filename)
            else:
                return pd.DataFrame()
        except Exception as e:
            raise Exception(f"Failed to load results from {filename}: {str(e)}")
    
    def get_recent_results_files(self, days=7):
        """Get list of recent result files"""
        try:
            export_dir = 'export'
            if not os.path.exists(export_dir):
                return []
            
            files = []
            for filename in os.listdir(export_dir):
                if filename.startswith('results_') and filename.endswith('.csv'):
                    filepath = os.path.join(export_dir, filename)
                    files.append(filepath)
            
            # Sort by modification time, most recent first
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            return files[:days]  # Return last N files
            
        except Exception as e:
            print(f"Warning: Failed to get recent files: {str(e)}")
            return []
    
    def get_history_stats(self):
        """Get statistics about the history file"""
        try:
            if not os.path.exists(self.history_file):
                return {'total_videos': 0, 'oldest_date': None, 'newest_date': None}
            
            history_df = pd.read_csv(self.history_file)
            
            return {
                'total_videos': len(history_df),
                'oldest_date': history_df['first_seen_date'].min() if not history_df.empty else None,
                'newest_date': history_df['first_seen_date'].max() if not history_df.empty else None
            }
            
        except Exception as e:
            print(f"Warning: Failed to get history stats: {str(e)}")
            return {'total_videos': 0, 'oldest_date': None, 'newest_date': None}
    
    def clear_history_older_than(self, days):
        """Remove history entries older than <days> days (0 = no action)."""
        try:
            if not os.path.exists(self.history_file) or days <= 0:
                return
            cutoff = datetime.now() - timedelta(days=days)
            df = pd.read_csv(self.history_file)
            df['first_seen_date'] = pd.to_datetime(df['first_seen_date'], errors='coerce')
            df = df[df['first_seen_date'] >= cutoff]
            df.to_csv(self.history_file, index=False)
            print(f"Auto-cleared history older than {days} days")
        except Exception as e:
            print(f"Warning: could not auto-clear history: {e}")

    def clear_history_now(self):
        """Immediately delete the entire history file."""
        self.clear_history()
