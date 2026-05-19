"""
Browser Manager Module
Handles launching and controlling a browser instance via Discord chat
Detects URLs in raw messages and navigates an Edge browser using Selenium
Keeps the same browser instance and tab so Discord streams stay connected
Supports windowed/fullscreen toggle, autoplay, and ad blocking
"""

import configparser
import asyncio
import threading
import time
from pathlib import Path

from browser_support.autoplay import AUTOPLAY_SCRIPT
from browser_support.bookmarks import (
    add_bookmark,
    load_bookmarks,
    remove_bookmark,
    resolve_bookmark,
    save_bookmarks,
)
from browser_support.urls import URL_PATTERN, ensure_https, is_valid_url, parse_url_with_name


class BrowserManager:
    """Manages a browser controlled via Discord messages using Selenium"""

    APPROVE_LINK_EMOJI = '🌐'
    CONTROL_EMOJIS = {
        '⬅️': 'back',
        '➡️': 'forward',
        '🔄': 'refresh',
        '❌': 'close',
        '🖥️': 'toggle_fullscreen',
    }

    # Compatibility aliases for code/tests that may access these constants on the class.
    URL_PATTERN = URL_PATTERN
    AUTOPLAY_SCRIPT = AUTOPLAY_SCRIPT

    def __init__(self, client, config_path='config.ini'):
        """
        Initialize the Browser Manager

        Args:
            client: Discord client instance
            config_path: Path to configuration file
        """
        self.client = client
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(config_path, encoding='utf-8')

        # Load configuration
        self.server_id = int(self.config['Discord']['server_id'])
        self.designated_channel_id = int(self.config['Discord']['designated_channel_id'])
        self.admin_role_id = int(self.config['Roles']['admin_role_id'])

        # Browser configuration
        if 'Browser' in self.config:
            browser_config = self.config['Browser']
            self.browser_path = browser_config.get('browser_path', 'auto')
            self.window_width = browser_config.getint('window_width', 1920)
            self.window_height = browser_config.getint('window_height', 1080)
            self.autoplay = browser_config.getboolean('autoplay', True)
            self.adblock_extension_path = browser_config.get('adblock_extension_path', '')
        else:
            self.browser_path = 'auto'
            self.window_width = 1920
            self.window_height = 1080
            self.autoplay = True
            self.adblock_extension_path = ''

        # Bookmark file path
        if getattr(__import__('sys'), 'frozen', False):
            self._app_path = Path(__import__('sys').executable).parent
        else:
            self._app_path = Path(__file__).parent
        self.bookmarks_file = self._app_path / 'bookmarks.json'

        # Track browser state
        self.driver = None
        self.current_url = None
        self.is_fullscreen = False
        self._browser_lock = threading.Lock()
        self.pending_links = {}  # {message_id: {url, bookmark_name, channel_id}}
        self.approved_links = {}  # {message_id: {url, channel_id}} links that can be reopened via 🌐
        self.control_message_ids = set()
        self._processing_links = set()   # guard against double-open on rapid emoji clicks
        self._active_message_id = None   # message ID of the currently-open browser session
        self._last_interaction_time = None  # time.time() of last browser interaction
        self._nav_count = 0              # number of pages navigated (for back eligibility)
        self._backed_steps = 0           # number of back steps taken (for forward eligibility)
        self._loop = None                # asyncio loop used for Discord cleanup callbacks

        # Load bookmarks
        self.bookmarks = self._load_bookmarks()

        # Start idle watchdog (closes browser after 3 h of no interaction)
        self._idle_watchdog_thread = threading.Thread(
            target=self._idle_watchdog, daemon=True
        )
        self._idle_watchdog_thread.start()

        print(f"BrowserManager initialized (channel: {self.designated_channel_id})")
        print(f"[Browser] Loaded {len(self.bookmarks)} bookmarks")

    def _ensure_https(self, url):
        """Ensure URL has https:// prefix."""
        return ensure_https(url)

    def _is_valid_url(self, url):
        """Check if the URL looks valid."""
        return is_valid_url(url)

    def _inject_scripts(self):
        """Inject autoplay and ad-skip scripts into the current page"""
        if self.driver is None:
            return

        try:
            if self.autoplay:
                self.driver.execute_script(self.AUTOPLAY_SCRIPT)
                print("[Browser] Injected autoplay + ad-skip scripts")
        except Exception as e:
            print(f"[Browser] Error injecting scripts: {e}")

    def _press_spacebar(self):
        """
        Press the spacebar on the current page as a universal play trigger.
        Clicks the page body first to ensure the browser (not the address bar) has focus,
        then dispatches a Space keypress — works on virtually any embedded player.
        """
        if self.driver is None:
            return
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            # Focus the page body so the keypress goes to the player, not the URL bar
            self.driver.execute_script("document.body.click();")
            ActionChains(self.driver).send_keys(Keys.SPACE).perform()
            print("[Browser] Sent spacebar keypress to page")
        except Exception as e:
            print(f"[Browser] Error sending spacebar: {e}")

    def _inject_scripts_delayed(self):
        """Inject scripts after a delay, then press spacebar as a universal fallback"""
        def _delayed():
            time.sleep(3)  # Wait for page to load
            self._inject_scripts()
            # Small extra pause so the player has time to initialise before space is sent
            time.sleep(1)
            self._press_spacebar()
        t = threading.Thread(target=_delayed, daemon=True)
        t.start()

    def _idle_watchdog(self):
        """
        Background thread: auto-close the browser after 3 hours of no interaction.
        Checks every 5 minutes.
        """
        idle_timeout = 3 * 3600  # 3 hours in seconds
        check_interval = 5 * 60  # 5 minutes
        while True:
            time.sleep(check_interval)
            try:
                if self.driver is not None and self._last_interaction_time is not None:
                    idle_seconds = time.time() - self._last_interaction_time
                    if idle_seconds >= idle_timeout:
                        print(
                            f"[Browser] Idle for {idle_seconds / 3600:.1f} h — auto-closing browser"
                        )
                        if self._close_sync():
                            self._schedule_browser_control_cleanup()
            except Exception as e:
                print(f"[Browser] Idle watchdog error: {e}")

    def _touch_interaction(self):
        """Record the current time as the last browser interaction timestamp."""
        self._last_interaction_time = time.time()

    def _remember_loop(self):
        """Remember the running asyncio loop so background threads can schedule cleanup."""
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

    def _is_browser_alive_sync(self):
        """Return True only when Selenium still has a live browser window."""
        if self.driver is None:
            return False

        try:
            # Accessing window_handles forces Selenium to contact the browser. If the
            # user closed the browser manually, this raises or returns no handles.
            return bool(self.driver.window_handles)
        except Exception:
            return False

    def _reset_browser_state(self):
        """Reset internal state after the browser becomes unavailable."""
        self.driver = None
        self.current_url = None
        self.is_fullscreen = False
        self._active_message_id = None
        self._last_interaction_time = None
        self._nav_count = 0
        self._backed_steps = 0

    async def _ensure_browser_available(self):
        """Detect externally-closed browsers and remove stale Discord controls."""
        self._remember_loop()
        if self.driver is None:
            await self._cleanup_browser_controls()
            return False

        loop = asyncio.get_event_loop()
        alive = await loop.run_in_executor(None, self._is_browser_alive_sync)
        if alive:
            return True

        print("[Browser] Browser is no longer available — cleaning up stale controls")
        self._reset_browser_state()
        await self._cleanup_browser_controls()
        return False

    async def _remove_reactions_by_emoji(self, message, emojis):
        """Remove all reactions for the supplied emojis from a Discord message."""
        for emoji in emojis:
            try:
                await message.clear_reaction(emoji)
            except Exception:
                # Fallback for limited permissions: remove only the bot's reaction.
                try:
                    if self.client.user:
                        await message.remove_reaction(emoji, self.client.user)
                except Exception as e:
                    print(f"[Browser] Could not remove stale reaction {emoji}: {e}")

    async def _cleanup_browser_controls(self, message_id=None, channel_id=None):
        """Remove browser approval/control/status reactions that are no longer available."""
        self._remember_loop()

        ids_to_cleanup = set(self.control_message_ids)
        if self._active_message_id:
            ids_to_cleanup.add(self._active_message_id)
        if message_id:
            ids_to_cleanup.add(message_id)

        if not ids_to_cleanup:
            return

        # Remove only unavailable browser controls/status. Keep 🌐 so the same
        # message can be clicked again to reopen the link after the browser closes.
        emojis = list(self.CONTROL_EMOJIS.keys()) + ['✅']
        channel = self.client.get_channel(channel_id or self.designated_channel_id)
        if not channel:
            try:
                channel = await self.client.fetch_channel(channel_id or self.designated_channel_id)
            except Exception as e:
                print(f"[Browser] Could not fetch channel for stale control cleanup: {e}")
                return

        for msg_id in list(ids_to_cleanup):
            try:
                message = await channel.fetch_message(msg_id)
            except Exception as e:
                print(f"[Browser] Could not fetch control message {msg_id} for cleanup: {e}")
                self.control_message_ids.discard(msg_id)
                continue

            await self._remove_reactions_by_emoji(message, emojis)
            self.control_message_ids.discard(msg_id)

    def _schedule_browser_control_cleanup(self):
        """Schedule stale control cleanup from non-async contexts such as watchdog threads."""
        if not self._loop or not self._loop.is_running():
            return
        try:
            asyncio.run_coroutine_threadsafe(self._cleanup_browser_controls(), self._loop)
        except Exception as e:
            print(f"[Browser] Could not schedule stale control cleanup: {e}")

    def _launch_browser_sync(self, url):
        """
        Launch the browser in windowed mode with the given URL (blocking).
        Uses Selenium WebDriver for persistent tab control.

        Args:
            url: URL to navigate to

        Returns:
            bool: True if launched successfully
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.edge.options import Options
            from selenium.webdriver.edge.service import Service
        except ImportError:
            print("Error: selenium not installed! Run: pip install selenium")
            return False

        try:
            options = Options()

            # Windowed mode - maximized with title bar (no kiosk)
            options.add_argument(f'--window-size={self.window_width},{self.window_height}')
            options.add_argument('--start-maximized')

            # Performance options
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--log-level=3')          # Suppress verbose browser logging
            options.add_argument('--silent-debugger-extension-api')  # Suppress uBlock/extension DevTools noise

            # If a specific browser path is configured, use it
            if self.browser_path and self.browser_path != 'auto':
                options.binary_location = self.browser_path

            # Load uBlock Origin extension if configured (must be an unpacked directory)
            if self.adblock_extension_path:
                ext_path = Path(self.adblock_extension_path)
                if ext_path.exists() and (ext_path / 'manifest.json').exists():
                    # Use --load-extension for unpacked extension directory
                    options.add_argument(f'--load-extension={str(ext_path.resolve())}')
                    print(f"[Browser] Loaded ad blocker extension: {ext_path}")
                else:
                    options.add_argument('--disable-extensions')
                    print(f"[Browser] Warning: Ad blocker extension not found at {ext_path} (need directory with manifest.json)")
            else:
                # No ad blocker - disable all extensions for performance
                options.add_argument('--disable-extensions')

            # Create WebDriver - Selenium 4.6+ auto-manages the driver
            self.driver = webdriver.Edge(options=options)
            self.driver.get(url)

            self.current_url = url
            self.is_fullscreen = False
            self._touch_interaction()
            self._nav_count += 1
            self._backed_steps = 0  # new launch clears forward history

            # Inject autoplay and ad-skip scripts after page loads
            self._inject_scripts_delayed()

            print(f"Browser launched in windowed mode: {url}")
            return True

        except Exception as e:
            print(f"Error launching browser: {e}")
            self.driver = None
            return False

    def _navigate_sync(self, url):
        """
        Navigate the existing browser tab to a new URL (blocking).
        Keeps the same browser window and tab.

        Args:
            url: URL to navigate to

        Returns:
            bool: True if navigated successfully
        """
        if self.driver is None:
            return self._launch_browser_sync(url)

        try:
            self.driver.get(url)
            self.current_url = url
            self._touch_interaction()
            self._nav_count += 1
            self._backed_steps = 0  # new navigation clears forward history

            # Inject autoplay and ad-skip scripts after page loads
            self._inject_scripts_delayed()

            print(f"Browser navigated to: {url}")
            return True
        except Exception as e:
            print(f"Error navigating browser: {e}")
            # Driver might be stale, try relaunching
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            self.current_url = None
            self.is_fullscreen = False
            return self._launch_browser_sync(url)

    def _refresh_sync(self):
        """
        Refresh the current page (blocking)

        Returns:
            bool: True if refreshed successfully
        """
        if self.driver is None:
            print("No browser is currently open")
            return False

        try:
            self.driver.refresh()
            self._touch_interaction()
            # Re-inject scripts after refresh
            self._inject_scripts_delayed()
            print("Browser refreshed")
            return True
        except Exception as e:
            print(f"Error refreshing browser: {e}")
            return False

    def _back_sync(self):
        """Navigate browser history backward."""
        if self.driver is None:
            print("No browser is currently open")
            return False

        try:
            self.driver.back()
            self.current_url = self.driver.current_url
            self._touch_interaction()
            self._backed_steps += 1
            self._inject_scripts_delayed()
            print("Browser went back")
            return True
        except Exception as e:
            print(f"Error going back: {e}")
            return False

    def _forward_sync(self):
        """Navigate browser history forward."""
        if self.driver is None:
            print("No browser is currently open")
            return False

        try:
            self.driver.forward()
            self.current_url = self.driver.current_url
            self._touch_interaction()
            self._backed_steps = max(0, self._backed_steps - 1)
            self._inject_scripts_delayed()
            print("Browser went forward")
            return True
        except Exception as e:
            print(f"Error going forward: {e}")
            return False

    def _close_sync(self):
        """
        Close the browser instance (blocking)

        Returns:
            bool: True if closed successfully
        """
        if self.driver is None:
            print("No browser to close")
            return False

        try:
            self.driver.quit()
            self._reset_browser_state()
            print("Browser closed")
            return True
        except Exception as e:
            print(f"Error closing browser: {e}")
            self._reset_browser_state()
            return False

    def _toggle_fullscreen_sync(self):
        """
        Toggle between fullscreen and windowed mode (blocking)

        Returns:
            tuple: (bool success, str new_state)
        """
        if self.driver is None:
            print("No browser is currently open")
            return False, "none"

        try:
            if self.is_fullscreen:
                # Currently fullscreen, switch to windowed
                self.driver.maximize_window()
                self.is_fullscreen = False
                print("[Browser] Switched to windowed mode")
                return True, "windowed"
            else:
                # Currently windowed, switch to fullscreen (F11-style)
                self.driver.fullscreen_window()
                self.is_fullscreen = True
                print("[Browser] Switched to fullscreen mode")
                return True, "fullscreen"
        except Exception as e:
            print(f"Error toggling fullscreen: {e}")
            return False, "error"

    def _minimize_sync(self):
        """
        Minimize the browser window / restore to windowed mode (blocking)

        Returns:
            bool: True if minimized successfully
        """
        if self.driver is None:
            print("No browser is currently open")
            return False

        try:
            self.driver.maximize_window()
            self.is_fullscreen = False
            print("[Browser] Restored to windowed mode")
            return True
        except Exception as e:
            print(f"Error restoring window: {e}")
            return False

    async def launch_browser(self, url):
        """
        Launch the browser in windowed mode (async wrapper)

        Args:
            url: URL to navigate to

        Returns:
            bool: True if launched successfully
        """
        self._remember_loop()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._launch_browser_sync, url)

    async def navigate_browser(self, url):
        """
        Navigate the existing browser tab to a new URL (async wrapper)

        Args:
            url: URL to navigate to

        Returns:
            bool: True if navigated successfully
        """
        self._remember_loop()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._navigate_sync, url)

    async def close_browser(self):
        """
        Close the browser instance (async wrapper)

        Returns:
            bool: True if closed successfully
        """
        self._remember_loop()
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, self._close_sync)
        if success:
            await self._cleanup_browser_controls()
        return success

    async def refresh_browser(self):
        """
        Refresh the browser page (async wrapper)

        Returns:
            bool: True if refreshed successfully
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._refresh_sync)

    async def back_browser(self):
        """Go back in browser history (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._back_sync)

    async def forward_browser(self):
        """Go forward in browser history (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._forward_sync)

    async def toggle_fullscreen(self):
        """
        Toggle between fullscreen and windowed mode (async wrapper)

        Returns:
            tuple: (bool success, str new_state)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._toggle_fullscreen_sync)

    async def minimize_browser(self):
        """
        Restore browser to windowed mode with title bar (async wrapper)

        Returns:
            bool: True if restored successfully
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._minimize_sync)

    def _load_bookmarks(self):
        """Load bookmarks from JSON file."""
        return load_bookmarks(self.bookmarks_file)

    def _save_bookmarks(self):
        """Save bookmarks to JSON file."""
        save_bookmarks(self.bookmarks_file, self.bookmarks)

    def _add_bookmark(self, name, url):
        """Add a bookmark."""
        add_bookmark(self.bookmarks_file, self.bookmarks, name, url)

    def _remove_bookmark(self, name):
        """Remove a bookmark."""
        return remove_bookmark(self.bookmarks_file, self.bookmarks, name)

    def _resolve_bookmark(self, content):
        """Check if content matches a bookmark name and return the URL."""
        return resolve_bookmark(self.bookmarks, content)

    def _has_admin_role(self, user_roles):
        """
        Check if user has the admin role

        Args:
            user_roles: List of Discord role objects

        Returns:
            bool: True if user has admin role
        """
        return any(role.id == self.admin_role_id for role in user_roles)

    async def _add_browser_controls(self, message):
        """
        Add applicable browser control reactions to a Discord message.

        Only adds emojis that make sense given the current browser state:
          ⬅️  Back        — only if there is history to go back to (_nav_count >= 1)
          ➡️  Forward     — only if the user has gone back at least once (_backed_steps > 0)
          🔄  Refresh     — always (browser is open)
          ❌  Close       — always (browser is open)
          🖥️  Fullscreen  — always (browser is open)
        """
        self.control_message_ids.add(message.id)

        for emoji, action in self.CONTROL_EMOJIS.items():
            # Determine whether this control is currently applicable
            if action == 'back' and self._nav_count < 1:
                continue   # no history yet — skip back arrow
            if action == 'forward' and self._backed_steps <= 0:
                continue   # haven't gone back — skip forward arrow

            try:
                await message.add_reaction(emoji)
            except Exception as e:
                print(f"[Browser] Could not add control {emoji}: {e}")

    async def _open_approved_link(self, message_id, actor=None):
        """Open a pending link after approval by an authorized role."""
        # Guard: prevent multiple simultaneous opens for the same message
        if message_id in self._processing_links:
            print(f"[Browser] Link {message_id} is already being processed — ignoring duplicate reaction")
            return False
        self._processing_links.add(message_id)

        try:
            pending = self.pending_links.get(message_id) or self.approved_links.get(message_id)
            if not pending:
                return False

            url = pending['url']
            bookmark_name = pending.get('bookmark_name')
            channel_id = pending.get('channel_id')

            if bookmark_name:
                self._add_bookmark(bookmark_name, url)

            if self.driver is not None:
                success = await self.navigate_browser(url)
                action = "Navigated to"
            else:
                success = await self.launch_browser(url)
                action = "Launched browser with"

            channel = self.client.get_channel(channel_id) if channel_id else None
            if channel:
                try:
                    message = await channel.fetch_message(message_id)
                    if success:
                        await self._add_browser_controls(message)
                    else:
                        await message.add_reaction('❌')
                except Exception as e:
                    print(f"[Browser] Could not update approved link message: {e}")

            if success:
                self.pending_links.pop(message_id, None)
                self.approved_links[message_id] = {
                    'url': url,
                    'channel_id': channel_id,
                }
                self._active_message_id = message_id
                actor_name = getattr(actor, 'display_name', 'approved user') if actor else 'approved user'
                print(f"[Browser] {action}: {url} (approved by {actor_name})")
            else:
                print(f"[Browser] Failed to open approved link: {url}")
            return success
        finally:
            self._processing_links.discard(message_id)

    async def _run_browser_control(self, emoji, actor=None):
        """Run a browser action mapped to a reaction emoji."""
        action = self.CONTROL_EMOJIS.get(emoji)
        if not action:
            return False

        if not await self._ensure_browser_available():
            actor_name = getattr(actor, 'display_name', 'approved user') if actor else 'approved user'
            print(f"[Browser] Ignored stale control {emoji} from {actor_name}; browser is closed")
            return True

        if action == 'back':
            success = await self.back_browser()
        elif action == 'forward':
            success = await self.forward_browser()
        elif action == 'refresh':
            success = await self.refresh_browser()
        elif action == 'close':
            success = await self.close_browser()
        elif action == 'toggle_fullscreen':
            success, _ = await self.toggle_fullscreen()
        else:
            return False

        # Touch interaction time for all control actions (except close which resets it)
        if success and action != 'close':
            self._touch_interaction()

        actor_name = getattr(actor, 'display_name', 'approved user') if actor else 'approved user'
        print(f"[Browser] Reaction control {emoji} -> {action} by {actor_name}: {'ok' if success else 'failed'}")
        return True

    async def _delete_message(self, message):
        """Delete a Discord message if possible."""
        try:
            await message.delete()
            print(f"[Browser] Deleted caller message {message.id}")
            return True
        except Exception as e:
            print(f"[Browser] Could not delete caller message {getattr(message, 'id', 'unknown')}: {e}")
            return False

    async def _delete_message_by_id(self, channel_id, message_id):
        """Fetch and delete a Discord message by channel/message ID."""
        channel = self.client.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.client.fetch_channel(channel_id)
            except Exception as e:
                print(f"[Browser] Could not fetch channel {channel_id} for deletion: {e}")
                return False

        try:
            message = await channel.fetch_message(message_id)
        except Exception as e:
            print(f"[Browser] Could not fetch caller message {message_id}: {e}")
            return False

        return await self._delete_message(message)

    async def handle_raw_reaction(self, payload, added=True):
        """
        Handle browser approval/control reactions.

        Only reaction-add events are allowed to trigger browser actions. Reaction
        removals are ignored so lowering/removing an emoji count cannot open or
        control the browser.
        """
        if not added:
            return False

        if payload.channel_id != self.designated_channel_id:
            return False

        if self.client.user and payload.user_id == self.client.user.id:
            return False

        emoji = str(payload.emoji)
        if emoji != self.APPROVE_LINK_EMOJI and emoji not in self.CONTROL_EMOJIS:
            return False

        guild = self.client.get_guild(payload.guild_id) if payload.guild_id else None
        if not guild:
            return False

        member = payload.member if added and getattr(payload, 'member', None) else guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except Exception as e:
                print(f"[Browser] Could not fetch reaction member {payload.user_id}: {e}")
                return False

        if not self._has_admin_role(member.roles):
            return False

        if emoji == self.APPROVE_LINK_EMOJI and (
            payload.message_id in self.pending_links
            or payload.message_id in self.approved_links
        ):
            return await self._open_approved_link(payload.message_id, member)

        if emoji in self.CONTROL_EMOJIS and payload.message_id in self.control_message_ids:
            handled = await self._run_browser_control(emoji, member)
            if handled and self.CONTROL_EMOJIS.get(emoji) == 'close':
                await self._delete_message_by_id(payload.channel_id, payload.message_id)
                self.control_message_ids.discard(payload.message_id)
            return handled

        return False

    def parse_url_with_name(self, content):
        """
        Parse a URL and optional bookmark name from message content.

        Args:
            content: Message content string

        Returns:
            tuple: (url, bookmark_name) where bookmark_name is None if not provided
        """
        return parse_url_with_name(content)

    async def process_message(self, message):
        """
        Process incoming messages for browser control

        Args:
            message: Discord message object

        Returns:
            bool: True if message was handled, False otherwise
        """
        # Only process messages in the designated channel
        if message.channel.id != self.designated_channel_id:
            return False

        # Ignore bot messages
        if message.author.bot:
            return False

        content = message.content.strip()
        content_lower = content.lower()

        # Ignore messages containing ! because they are usually commands for other bots
        if '!' in content:
            return False

        # Handle 'bookmarks' / 'bm' command - list all bookmarks
        if content_lower in ('bookmarks', 'bm'):
            if not self._has_admin_role(message.author.roles):
                return False
            if self.bookmarks:
                lines = ["📑 **Bookmarks:**"]
                for name, url in sorted(self.bookmarks.items()):
                    lines.append(f"  • `{name}` → {url}")
                await message.reply('\n'.join(lines))
            else:
                await message.reply("📑 No bookmarks saved yet.\nUse: `https://example.com name` to create one.")
            print("[Browser] Listed bookmarks")
            return True

        # Handle 'del <name>' command - delete a bookmark
        if content_lower.startswith('del '):
            if not self._has_admin_role(message.author.roles):
                return False
            name = content[4:].strip()
            if name:
                removed = self._remove_bookmark(name)
                if removed:
                    await message.add_reaction('🗑️')
                    print(f"[Browser] Deleted bookmark: {name}")
                else:
                    await message.add_reaction('❌')
                    print(f"[Browser] Bookmark not found: {name}")
            return True

        # Handle 'refresh' command
        if content_lower == 'refresh':
            if not self._has_admin_role(message.author.roles):
                return False
            success = await self.refresh_browser()
            if success:
                await message.add_reaction('🔄')
                print("[Browser] Refreshed page")
            else:
                await message.add_reaction('❌')
                print("[Browser] No browser to refresh")
            return True

        # Handle 'close' command
        if content_lower == 'close':
            if not self._has_admin_role(message.author.roles):
                return False
            success = await self.close_browser()
            if success:
                await self._delete_message(message)
                print("[Browser] Closed browser")
            else:
                await message.add_reaction('❌')
                print("[Browser] No browser to close")
            return True

        # Handle 'full' / 'max' / 'fullscreen' - toggle fullscreen on/off
        if content_lower in ('full', 'max', 'fullscreen'):
            if not self._has_admin_role(message.author.roles):
                return False
            success, new_state = await self.toggle_fullscreen()
            if success:
                if new_state == 'fullscreen':
                    await message.add_reaction('🖥️')
                    print("[Browser] Toggled to fullscreen")
                else:
                    await message.add_reaction('🔳')
                    print("[Browser] Toggled to windowed")
            else:
                await message.add_reaction('❌')
                print("[Browser] No browser to toggle")
            return True

        # Handle 'min' - restore to windowed mode (show title bar + X button)
        if content_lower == 'min':
            if not self._has_admin_role(message.author.roles):
                return False
            success = await self.minimize_browser()
            if success:
                await message.add_reaction('🔳')
                print("[Browser] Restored to windowed mode")
            else:
                await message.add_reaction('❌')
                print("[Browser] No browser to minimize")
            return True

        # Try to parse a URL (with optional bookmark name)
        url, bookmark_name = self.parse_url_with_name(content)
        if url:
            # Save as bookmark if name was provided
            self.pending_links[message.id] = {
                'url': url,
                'bookmark_name': bookmark_name,
                'channel_id': message.channel.id,
            }
            await message.add_reaction(self.APPROVE_LINK_EMOJI)
            print(
                f"[Browser] Link pending approval: {url}"
                + (f" (bookmark: '{bookmark_name}')" if bookmark_name else "")
            )
            return True

        # Check if the message matches a bookmark name
        bookmark_url = self._resolve_bookmark(content)
        if bookmark_url:
            if not self._has_admin_role(message.author.roles):
                return False
            if self.driver is not None:
                success = await self.navigate_browser(bookmark_url)
                if success:
                    await message.add_reaction('🔖')
                    print(f"[Browser] Bookmark '{content_lower}' → {bookmark_url}")
                else:
                    await message.add_reaction('❌')
            else:
                success = await self.launch_browser(bookmark_url)
                if success:
                    await message.add_reaction('🔖')
                    print(f"[Browser] Bookmark '{content_lower}' → {bookmark_url}")
                else:
                    await message.add_reaction('❌')
            return True

        return False

    async def handle_message_delete(self, message):
        """
        Handle Discord message deletion.
        If the deleted message is the active browser session's source message,
        auto-close the browser.

        Args:
            message: Discord message object (may have limited data after deletion)
        """
        msg_id = message.id
        # Close browser if the controlling message was deleted
        if msg_id == self._active_message_id or msg_id in self.control_message_ids:
            if self.driver is not None:
                print(f"[Browser] Controlling message {msg_id} was deleted — auto-closing browser")
                await self.close_browser()
            # Clean up tracking sets
            self.control_message_ids.discard(msg_id)
            if self._active_message_id == msg_id:
                self._active_message_id = None

    def register_commands(self, bot):
        """Register browser-related commands (no prefix commands needed - raw parsing only)"""
        pass
