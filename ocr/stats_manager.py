"""
Stats Manager for tracking player statistics across multiple matches
Stores data in JSON format and provides leaderboard functionality
"""

import json
import os
from datetime import datetime


class StatsManager:
    """Manage player statistics storage and retrieval"""
    
    def __init__(self, data_file='ocr/stats_data.json'):
        """
        Initialize the stats manager
        
        Args:
            data_file: Path to JSON file for storing stats
        """
        self.data_file = data_file
        self.screenshot_log_file = data_file.replace('stats_data.json', 'screenshot_log.json')
        self.stats = {}
        self.duos_stats = {}  # Track duos-specific stats
        self.squads_stats = {}  # Track squads-specific stats
        self.screenshot_log = {}  # Track processed screenshots
        self.load_stats()
        self.load_screenshot_log()
    
    def load_stats(self):
        """Load stats from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Support both old format (dict) and new format (dict with mode keys)
                    if 'overall' in data or 'duos' in data or 'squads' in data:
                        # New format with mode separation
                        self.stats = data.get('overall', {})
                        self.duos_stats = data.get('duos', {})
                        self.squads_stats = data.get('squads', {})
                    else:
                        # Old format - treat as overall stats
                        self.stats = data
                        self.duos_stats = {}
                        self.squads_stats = {}
                print(f"Loaded stats for {len(self.stats)} players overall, {len(self.duos_stats)} duos, {len(self.squads_stats)} squads")
            except Exception as e:
                print(f"Error loading stats: {e}")
                self.stats = {}
                self.duos_stats = {}
                self.squads_stats = {}
        else:
            print("No existing stats file found, starting fresh")
            self.stats = {}
            self.duos_stats = {}
            self.squads_stats = {}
    
    def save_stats(self):
        """Save stats to JSON file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            
            # Save in new format with mode separation
            data = {
                'overall': self.stats,
                'duos': self.duos_stats,
                'squads': self.squads_stats
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Stats saved for {len(self.stats)} players overall, {len(self.duos_stats)} duos, {len(self.squads_stats)} squads")
        except Exception as e:
            print(f"Error saving stats: {e}")
    
    def update_player_stats(self, parsed_data):
        """
        Update stats for all players from a parsed screenshot
        
        Args:
            parsed_data: Dictionary with 'match_time', 'game_mode', and 'players' list
        """
        if not parsed_data or 'players' not in parsed_data:
            return
        
        match_time = parsed_data.get('match_time', 0)
        game_mode = parsed_data.get('game_mode', 'squads')  # Default to squads if not specified
        
        # Select the appropriate stats dictionary based on game mode
        if game_mode == 'duos':
            mode_stats = self.duos_stats
        elif game_mode == 'squads':
            mode_stats = self.squads_stats
        else:
            mode_stats = self.squads_stats  # Default fallback
        
        for player_data in parsed_data['players']:
            name = player_data.get('name', '').strip()
            
            if not name:
                continue
            
            # Normalize name (case-insensitive storage)
            name_lower = name.lower()
            
            # Initialize player in overall stats if not exists
            if name_lower not in self.stats:
                self.stats[name_lower] = {
                    'display_name': name,  # Store original capitalization
                    'wins': 0,
                    'kills': 0,
                    'deaths': 0,
                    'assists': 0,
                    'score': 0,
                    'playtime': 0.0,
                    'games_played': 0
                }
            
            # Initialize player in mode-specific stats if not exists
            if name_lower not in mode_stats:
                mode_stats[name_lower] = {
                    'display_name': name,
                    'wins': 0,
                    'kills': 0,
                    'deaths': 0,
                    'score': 0,
                    'games_played': 0
                }
            
            # Determine playtime to use: individual if available, otherwise match_time
            if 'playtime_minutes' in player_data:
                # Use individual playtime from OCR detection
                player_playtime = player_data['playtime_minutes']
                print(f"  Using individual playtime for {name}: {player_playtime} minutes")
            else:
                # Fall back to match_time if individual playtime not detected
                player_playtime = match_time
                print(f"  Using match time for {name}: {player_playtime} minutes (individual playtime not detected)")
            
            # Update overall stats (accumulate totals)
            self.stats[name_lower]['wins'] += 1  # Each screenshot is a win
            self.stats[name_lower]['kills'] += player_data.get('kills', 0)
            self.stats[name_lower]['deaths'] += player_data.get('deaths', 0)
            self.stats[name_lower]['assists'] += player_data.get('assists', 0)
            self.stats[name_lower]['score'] += player_data.get('score', 0)
            self.stats[name_lower]['playtime'] += player_playtime
            self.stats[name_lower]['games_played'] += 1
            
            # Update mode-specific stats (no playtime or assists for mode tables)
            mode_stats[name_lower]['wins'] += 1
            mode_stats[name_lower]['kills'] += player_data.get('kills', 0)
            mode_stats[name_lower]['deaths'] += player_data.get('deaths', 0)
            mode_stats[name_lower]['score'] += player_data.get('score', 0)
            mode_stats[name_lower]['games_played'] += 1
            
            # Update display name if it's more complete
            if len(name) > len(self.stats[name_lower]['display_name']):
                self.stats[name_lower]['display_name'] = name
                mode_stats[name_lower]['display_name'] = name
        
        # Save after updating
        self.save_stats()
    
    def get_leaderboard(self, category='wins', min_games=2):
        """
        Get leaderboard sorted by category
        
        Args:
            category: Stat category to sort by (wins, kills, deaths, assists, score, playtime)
            min_games: Minimum games played to appear on leaderboard
            
        Returns:
            list: Sorted list of player stats dictionaries
        """
        # Filter players with minimum games
        eligible_players = [
            {**stats, 'name': name_key}
            for name_key, stats in self.stats.items()
            if stats['games_played'] >= min_games
        ]
        
        # Validate category
        valid_categories = ['wins', 'kills', 'deaths', 'assists', 'score', 'playtime', 'games_played']
        if category not in valid_categories:
            category = 'wins'
        
        # Sort by category (descending)
        sorted_players = sorted(
            eligible_players,
            key=lambda x: x.get(category, 0),
            reverse=True
        )
        
        return sorted_players
    
    def get_player_stats(self, name):
        """
        Get stats for a specific player (case-insensitive)
        
        Args:
            name: Player name
            
        Returns:
            dict: Player stats or None if not found
        """
        name_lower = name.lower()
        return self.stats.get(name_lower)
    
    def get_all_stats(self):
        """Get all player stats"""
        return self.stats
    
    def _format_discord_table(self, headers, rows, padding=2, alignments=None):
        """
        Format data as a Discord table with proper column alignment
        Similar to discord-table-builder package (PHP)
        
        Args:
            headers: List of column header strings
            rows: List of lists containing row data
            padding: Spaces between columns
            alignments: List of alignment types per column ('left', 'right', 'center')
                       Default: first column left, rest right-aligned
            
        Returns:
            str: Formatted table string
        """
        if not rows:
            return ""
        
        # Default alignments: first column (names) left, numbers right
        if alignments is None:
            alignments = ['left'] + ['right'] * (len(headers) - 1)
        
        # Calculate column widths based on content
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(str(header))
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(max_width)
        
        # Build table lines
        table_lines = []
        
        # Header row
        header_line = ""
        for i, header in enumerate(headers):
            if i < len(alignments):
                if alignments[i] == 'right':
                    header_line += str(header).rjust(col_widths[i]) + (' ' * padding)
                elif alignments[i] == 'center':
                    header_line += str(header).center(col_widths[i]) + (' ' * padding)
                else:  # left
                    header_line += str(header).ljust(col_widths[i]) + (' ' * padding)
            else:
                header_line += str(header).ljust(col_widths[i]) + (' ' * padding)
        table_lines.append(header_line.rstrip())
        
        # Data rows
        for row in rows:
            row_line = ""
            for i, cell in enumerate(row):
                if i < len(col_widths) and i < len(alignments):
                    if alignments[i] == 'right':
                        row_line += str(cell).rjust(col_widths[i]) + (' ' * padding)
                    elif alignments[i] == 'center':
                        row_line += str(cell).center(col_widths[i]) + (' ' * padding)
                    else:  # left
                        row_line += str(cell).ljust(col_widths[i]) + (' ' * padding)
                elif i < len(col_widths):
                    row_line += str(cell).ljust(col_widths[i]) + (' ' * padding)
            table_lines.append(row_line.rstrip())
        
        return "\n".join(table_lines)
    
    def get_mode_leaderboard(self, mode='squads', category='score', min_games=2):
        """
        Get mode-specific leaderboard sorted by category
        
        Args:
            mode: Game mode ('duos' or 'squads')
            category: Stat category to sort by (score, wins, kills, deaths)
            min_games: Minimum games played to appear on leaderboard
            
        Returns:
            list: Sorted list of player stats dictionaries
        """
        # Select the appropriate stats dictionary
        mode_stats = self.duos_stats if mode == 'duos' else self.squads_stats
        
        # Filter players with minimum games
        eligible_players = [
            {**stats, 'name': name_key}
            for name_key, stats in mode_stats.items()
            if stats['games_played'] >= min_games
        ]
        
        # Validate category
        valid_categories = ['wins', 'kills', 'deaths', 'score', 'games_played']
        if category not in valid_categories:
            category = 'score'
        
        # Sort by category (descending)
        sorted_players = sorted(
            eligible_players,
            key=lambda x: x.get(category, 0),
            reverse=True
        )
        
        return sorted_players
    
    def format_leaderboard_embed(self, category='score', min_games=2, top_n=6):
        """
        Format leaderboard embed with FOUR tables for Discord:
        1. Overall Score leaderboard (Score, Wins, Playtime)
        2. Overall K/D leaderboard (K/D, Assists, Ratio)
        3. Duos leaderboard (Score, Wins, K/D)
        4. Squads leaderboard (Score, Wins, K/D)
        
        Uses discord-table-builder style formatting:
        - No rank column (ordering implies rank)
        - Left-aligned player names
        - Right-aligned numeric columns
        - Each table as a separate field (not code blocks)
        - All tables have consistent column widths for vertical alignment
        
        Args:
            category: Unused (kept for compatibility), always shows all 4 tables
            min_games: Minimum games to display
            top_n: Number of top players to show (default: 6)
            
        Returns:
            dict: Embed data with 4 leaderboards as fields
        """
        # First pass: collect all rows to determine maximum column widths
        all_table_data = []
        fields = []
        
        # Collect all player names from all tables to determine max name width
        all_names = []
        
        # 1. Collect Overall Score data
        score_leaders = self.get_leaderboard('score', min_games)[:top_n]
        for player in score_leaders:
            all_names.append(player['display_name'][:20])
        
        # 2. Collect Overall K/D data
        kills_leaders = self.get_leaderboard('kills', min_games)[:top_n]
        for player in kills_leaders:
            all_names.append(player['display_name'][:20])
        
        # 3. Collect Duos data
        duos_leaders = self.get_mode_leaderboard('duos', 'score', min_games)[:top_n]
        for player in duos_leaders:
            all_names.append(player['display_name'][:20])
        
        # 4. Collect Squads data
        squads_leaders = self.get_mode_leaderboard('squads', 'score', min_games)[:top_n]
        for player in squads_leaders:
            all_names.append(player['display_name'][:20])
        
        # Calculate maximum name width (including headers)
        max_name_width = max(
            len('DUOS+SQUADS'),
            len('KILLS'),
            len('DUOS'),
            len('SQUADS'),
            max([len(name) for name in all_names]) if all_names else 0
        )
        
        # Now build all tables with consistent width
        # 1. KILLS Leaderboard Table (K/D, Assists, Ratio) - FIRST
        kills_headers = ['KILLS', 'K/D', 'Assists', 'Ratio']
        kills_rows = []
        
        for player in kills_leaders:
            name = player['display_name'][:20].ljust(max_name_width)
            kills = player['kills']
            deaths = player['deaths']
            assists = str(player['assists'])
            
            kd_str = f"{kills}-{deaths}"
            kd_ratio = kills / max(1, deaths)
            ratio_str = f"{kd_ratio:.2f}"
            
            kills_rows.append([name, kd_str, assists, ratio_str])
        
        # Only add table if there are actual players
        if kills_rows:
            kills_table = self._format_discord_table(
                [kills_headers[0].ljust(max_name_width)] + kills_headers[1:],
                kills_rows,
                padding=6,
                alignments=['left', 'right', 'right', 'right']
            )
            fields.append(self._table_to_field('\u200b', kills_table))
        
        # 2. Duos Leaderboard Table - SECOND (only if there are players)
        duos_headers = ['DUOS', 'Score', 'Wins', 'K/D']
        duos_rows = []
        
        for player in duos_leaders:
            name = player['display_name'][:20].ljust(max_name_width)
            score = f"{player['score']:,}"
            wins = str(player['wins'])
            
            kills = player['kills']
            deaths = player['deaths']
            kd_ratio = kills / max(1, deaths)
            kd_str = f"{kd_ratio:.2f}"
            
            duos_rows.append([name, score, wins, kd_str])
        
        # Only add table if there are actual players
        if duos_rows:
            duos_table = self._format_discord_table(
                [duos_headers[0].ljust(max_name_width)] + duos_headers[1:],
                duos_rows,
                padding=6,
                alignments=['left', 'right', 'right', 'right']
            )
            fields.append(self._table_to_field('\u200b', duos_table))
        
        # 3. Squads Leaderboard Table - THIRD (only if there are players)
        squads_headers = ['SQUADS', 'Score', 'Wins', 'K/D']
        squads_rows = []
        
        for player in squads_leaders:
            name = player['display_name'][:20].ljust(max_name_width)
            score = f"{player['score']:,}"
            wins = str(player['wins'])
            
            kills = player['kills']
            deaths = player['deaths']
            kd_ratio = kills / max(1, deaths)
            kd_str = f"{kd_ratio:.2f}"
            
            squads_rows.append([name, score, wins, kd_str])
        
        # Only add table if there are actual players
        if squads_rows:
            squads_table = self._format_discord_table(
                [squads_headers[0].ljust(max_name_width)] + squads_headers[1:],
                squads_rows,
                padding=6,
                alignments=['left', 'right', 'right', 'right']
            )
            fields.append(self._table_to_field('\u200b', squads_table))
        
        # 4. DUOS+SQUADS Combined Stats Leaderboard Table - LAST
        combined_headers = ['DUOS+SQUADS', 'Score', 'Wins', 'Time']
        combined_rows = []
        
        for player in score_leaders:
            name = player['display_name'][:20].ljust(max_name_width)
            score = f"{player['score']:,}"
            wins = str(player['wins'])
            
            # Format playtime
            playtime = player['playtime']
            hours = int(playtime // 60)
            minutes = int(playtime % 60)
            playtime_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            
            combined_rows.append([name, score, wins, playtime_str])
        
        # Only add table if there are actual players
        if combined_rows:
            combined_table = self._format_discord_table(
                [combined_headers[0].ljust(max_name_width)] + combined_headers[1:],
                combined_rows,
                padding=6,
                alignments=['left', 'right', 'right', 'right']
            )
            fields.append(self._table_to_field('\u200b', combined_table))
        
        return {
            'description': '',
            'color': 0x00D166,  # Green
            'fields': fields
        }
    
    def _table_to_field(self, field_name, table_string):
        """
        Convert a formatted table string to a Discord embed field
        Mimics the PHP discord-table-builder toField() method
        
        Args:
            field_name: Name of the field (e.g., 'Score', 'Kills')
            table_string: Formatted table as string with newlines
            
        Returns:
            dict: Discord embed field object
        """
        # Split table into lines and wrap each in backticks
        lines = table_string.split('\n')
        wrapped_lines = [f"`{line}`" for line in lines]
        
        return {
            'name': field_name,
            'value': '\n'.join(wrapped_lines),
            'inline': False
        }
    
    def recalculate_all_stats_from_log(self):
        """
        Recalculate all player stats from screenshot log
        This is a backup/recovery feature that rebuilds stats_data.json from screenshot_log.json
        
        Returns:
            tuple: (success: bool, message: str, stats_count: int)
        """
        try:
            if not self.screenshot_log:
                return (False, "No screenshot log found to recalculate from", 0)
            
            # Clear existing stats (all modes)
            self.stats = {}
            self.duos_stats = {}
            self.squads_stats = {}
            print("Cleared existing stats for recalculation")
            
            # Process each logged screenshot
            processed_count = 0
            for log_key, log_entry in self.screenshot_log.items():
                try:
                    # Reconstruct parsed_data format from log entry
                    parsed_data = {
                        'match_time': log_entry.get('match_time', 0),
                        'game_mode': log_entry.get('game_mode', 'squads'),  # Include game mode
                        'players': []
                    }
                    
                    # Add player data
                    for player in log_entry.get('players', []):
                        if isinstance(player, dict):
                            player_data = {
                                'name': player.get('name', ''),
                                'score': player.get('score', 0),
                                'kills': player.get('kills', 0),
                                'deaths': player.get('deaths', 0),
                                'assists': player.get('assists', 0)
                            }
                            if 'playtime_minutes' in player:
                                player_data['playtime_minutes'] = player['playtime_minutes']
                            parsed_data['players'].append(player_data)
                        elif isinstance(player, str):
                            # Old format - just player name
                            parsed_data['players'].append({
                                'name': player,
                                'score': 0,
                                'kills': 0,
                                'deaths': 0,
                                'assists': 0
                            })
                    
                    # Update stats using normal update method
                    if parsed_data['players']:
                        self.update_player_stats(parsed_data)
                        processed_count += 1
                        
                except Exception as e:
                    print(f"Error processing log entry {log_key}: {e}")
                    continue
            
            message = f"Successfully recalculated stats from {processed_count} screenshots"
            print(message)
            return (True, message, len(self.stats))
            
        except Exception as e:
            error_msg = f"Error recalculating stats: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return (False, error_msg, 0)
    
    def get_available_categories(self):
        """Get list of available stat categories"""
        return ['wins', 'kills', 'deaths', 'assists', 'score', 'playtime', 'games_played']
    
    def load_screenshot_log(self):
        """Load screenshot log from JSON file"""
        if os.path.exists(self.screenshot_log_file):
            try:
                with open(self.screenshot_log_file, 'r') as f:
                    self.screenshot_log = json.load(f)
                print(f"Loaded {len(self.screenshot_log)} screenshot entries")
            except Exception as e:
                print(f"Error loading screenshot log: {e}")
                self.screenshot_log = {}
        else:
            self.screenshot_log = {}
    
    def save_screenshot_log(self):
        """Save screenshot log to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.screenshot_log_file), exist_ok=True)
            with open(self.screenshot_log_file, 'w') as f:
                json.dump(self.screenshot_log, f, indent=2)
        except Exception as e:
            print(f"Error saving screenshot log: {e}")
    
    def is_screenshot_processed(self, message_id, attachment_id):
        """
        Check if a screenshot has already been processed
        
        Args:
            message_id: Discord message ID
            attachment_id: Discord attachment ID
            
        Returns:
            bool: True if already processed
        """
        key = f"{message_id}_{attachment_id}"
        return key in self.screenshot_log
    
    def log_screenshot(self, message_id, attachment_id, filename, parsed_data):
        """
        Log a processed screenshot with full player stats
        
        Args:
            message_id: Discord message ID
            attachment_id: Discord attachment ID
            filename: Screenshot filename
            parsed_data: Parsed player data (includes game_mode)
        """
        key = f"{message_id}_{attachment_id}"
        
        # Store full player stats for this match
        players_data = []
        for player in parsed_data.get('players', []):
            player_entry = {
                'name': player['name'],
                'score': player.get('score', 0),
                'kills': player.get('kills', 0),
                'deaths': player.get('deaths', 0),
                'assists': player.get('assists', 0)
            }
            # Include individual playtime if available
            if 'playtime_minutes' in player:
                player_entry['playtime_minutes'] = player['playtime_minutes']
            
            players_data.append(player_entry)
        
        self.screenshot_log[key] = {
            'message_id': str(message_id),
            'attachment_id': str(attachment_id),
            'filename': filename,
            'processed_at': datetime.now().isoformat(),
            'match_time': parsed_data.get('match_time', 0),
            'game_mode': parsed_data.get('game_mode', 'squads'),  # Store game mode
            'players': players_data  # Now includes full stats per player including playtime
        }
        self.save_screenshot_log()
    
    def remove_screenshot_stats(self, log_entry):
        """
        Remove stats associated with a deleted screenshot
        
        Args:
            log_entry: Screenshot log entry containing player data with full stats and game mode
        """
        players = log_entry.get('players', [])
        match_time = log_entry.get('match_time', 0)
        game_mode = log_entry.get('game_mode', 'squads')  # Get game mode from log
        
        # Select mode-specific stats dictionary
        if game_mode == 'duos':
            mode_stats = self.duos_stats
        else:
            mode_stats = self.squads_stats
        
        for player_data in players:
            # Handle both old format (string) and new format (dict)
            if isinstance(player_data, str):
                player_name = player_data
                player_stats = {}
                player_playtime = match_time  # Use match_time for old format
            else:
                player_name = player_data.get('name', '')
                player_stats = player_data
                # Use individual playtime if available, otherwise match_time
                player_playtime = player_stats.get('playtime_minutes', match_time)
            
            name_lower = player_name.lower()
            
            # Remove from overall stats
            if name_lower in self.stats:
                # Reverse the stats added from this match
                self.stats[name_lower]['wins'] = max(0, self.stats[name_lower]['wins'] - 1)
                self.stats[name_lower]['games_played'] = max(0, self.stats[name_lower]['games_played'] - 1)
                self.stats[name_lower]['playtime'] = max(0, self.stats[name_lower]['playtime'] - player_playtime)
                
                # Subtract individual stats if available
                if player_stats:
                    self.stats[name_lower]['kills'] = max(0, self.stats[name_lower]['kills'] - player_stats.get('kills', 0))
                    self.stats[name_lower]['deaths'] = max(0, self.stats[name_lower]['deaths'] - player_stats.get('deaths', 0))
                    self.stats[name_lower]['assists'] = max(0, self.stats[name_lower]['assists'] - player_stats.get('assists', 0))
                    self.stats[name_lower]['score'] = max(0, self.stats[name_lower]['score'] - player_stats.get('score', 0))
                
                # Remove player if they have no games left
                if self.stats[name_lower]['games_played'] == 0:
                    del self.stats[name_lower]
                    print(f"Removed player {player_name} from overall stats (no games remaining)")
            
            # Remove from mode-specific stats
            if name_lower in mode_stats and player_stats:
                mode_stats[name_lower]['wins'] = max(0, mode_stats[name_lower]['wins'] - 1)
                mode_stats[name_lower]['games_played'] = max(0, mode_stats[name_lower]['games_played'] - 1)
                mode_stats[name_lower]['kills'] = max(0, mode_stats[name_lower]['kills'] - player_stats.get('kills', 0))
                mode_stats[name_lower]['deaths'] = max(0, mode_stats[name_lower]['deaths'] - player_stats.get('deaths', 0))
                mode_stats[name_lower]['score'] = max(0, mode_stats[name_lower]['score'] - player_stats.get('score', 0))
                
                # Remove player from mode stats if they have no games left
                if mode_stats[name_lower]['games_played'] == 0:
                    del mode_stats[name_lower]
                    print(f"Removed player {player_name} from {game_mode} stats (no games remaining)")
        
        self.save_stats()
