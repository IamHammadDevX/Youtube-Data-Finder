import json
import os
import yaml
from datetime import datetime

class ConfigManager:
    def __init__(self):
        self.settings_file = 'settings.json'
        self.default_settings = self._get_default_settings()
    
    def _get_default_settings(self):
        """Get default application settings"""
        return {
            'keywords': 'product review\ntech unboxing',
            'duration': 'Any',
            'duration_min': '',
            'duration_max': '',
            'views_min': '',
            'views_max': '',
            'subs_min': '',
            'subs_max': '',
            'region': '',
            'language': '',
            'pages': '2',
            'api_cap': '9500',
            'skip_hidden': True,
            'fresh_search': False
        }
    
    def save_settings(self, settings):
        """Save settings to JSON file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Failed to save settings: {str(e)}")
            return False
    
    def load_settings(self):
        """Load settings from JSON file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged_settings = self.default_settings.copy()
                merged_settings.update(settings)
                return merged_settings
            else:
                return self.default_settings.copy()
        except Exception as e:
            print(f"Failed to load settings: {str(e)}")
            return self.default_settings.copy()
    
    def validate_settings(self, settings):
        """Validate settings and return error messages"""
        errors = []
        
        # Validate keywords
        keywords = settings.get('keywords', '').strip()
        if not keywords:
            errors.append("Keywords cannot be empty")
        
        # Validate numeric fields
        numeric_fields = {
            'pages': 'Pages per keyword',
            'api_cap': 'API cap',
            'duration_min': 'Duration min',
            'duration_max': 'Duration max',
            'views_min': 'Views min',
            'views_max': 'Views max',
            'subs_min': 'Subscribers min',
            'subs_max': 'Subscribers max'
        }
        
        for field, display_name in numeric_fields.items():
            value = settings.get(field, '').strip()
            if value:  # Only validate if not empty
                try:
                    num_value = float(value) if field.startswith('duration_') else int(value)
                    if num_value < 0:
                        errors.append(f"{display_name} must be non-negative")
                except ValueError:
                    errors.append(f"{display_name} must be a valid number")
        
        # Validate duration range
        if settings.get('duration') == 'Custom':
            duration_min = settings.get('duration_min', '').strip()
            duration_max = settings.get('duration_max', '').strip()
            
            if not duration_min and not duration_max:
                errors.append("Custom duration requires at least min or max value")
            
            if duration_min and duration_max:
                try:
                    min_val = float(duration_min)
                    max_val = float(duration_max)
                    if min_val >= max_val:
                        errors.append("Duration min must be less than duration max")
                except ValueError:
                    pass  # Already validated above
        
        # Validate view range
        views_min = settings.get('views_min', '').strip()
        views_max = settings.get('views_max', '').strip()
        if views_min and views_max:
            try:
                min_views = int(views_min)
                max_views = int(views_max)
                if min_views >= max_views:
                    errors.append("Views min must be less than views max")
            except ValueError:
                pass  # Already validated above
        
        # Validate subscriber range
        subs_min = settings.get('subs_min', '').strip()
        subs_max = settings.get('subs_max', '').strip()
        if subs_min and subs_max:
            try:
                min_subs = int(subs_min)
                max_subs = int(subs_max)
                if min_subs >= max_subs:
                    errors.append("Subscribers min must be less than subscribers max")
            except ValueError:
                pass  # Already validated above
        
        return errors
    
    def export_schedule_config(self, settings, schedule_time='09:00'):
        """Export settings for scheduled execution"""
        try:
            # Create schedule-specific settings
            schedule_settings = settings.copy()
            schedule_settings['schedule_time'] = schedule_time
            schedule_settings['created_at'] = datetime.now().isoformat()
            
            schedule_file = 'schedule_settings.json'
            with open(schedule_file, 'w', encoding='utf-8') as f:
                json.dump(schedule_settings, f, indent=2, ensure_ascii=False)
            
            return schedule_file
        except Exception as e:
            print(f"Failed to export schedule config: {str(e)}")
            return None
    
    def get_api_key_info(self):
        """Get information about the API key configuration"""
        api_key = os.getenv('YOUTUBE_API_KEY', '')
        
        if not api_key:
            return {
                'configured': False,
                'message': 'YouTube API Key not set. Please set YOUTUBE_API_KEY environment variable.'
            }
        
        # Mask the key for display
        masked_key = api_key[:8] + '*' * (len(api_key) - 12) + api_key[-4:] if len(api_key) > 12 else '*' * len(api_key)
        
        return {
            'configured': True,
            'masked_key': masked_key,
            'message': f'API Key configured: {masked_key}'
        }
    
    def create_task_scheduler_command(self, settings_file=None):
        """Generate Windows Task Scheduler command"""
        if not settings_file:
            settings_file = self.settings_file
        
        # Get current Python executable path
        python_exe = os.path.abspath('python.exe')
        if not os.path.exists(python_exe):
            python_exe = 'python'  # Fallback to system Python
        
        # Get absolute paths
        script_dir = os.path.abspath('.')
        app_script = os.path.join(script_dir, 'app_headless.py')
        settings_path = os.path.join(script_dir, settings_file)
        
        command = f'"{python_exe}" "{app_script}" --settings "{settings_path}"'
        
        return {
            'command': command,
            'working_directory': script_dir,
            'python_exe': python_exe,
            'script_path': app_script,
            'settings_path': settings_path
        }
