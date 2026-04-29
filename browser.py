"""
Browser Manager Module
Handles launching and controlling a browser instance via Discord chat
Detects URLs in raw messages and navigates an Edge browser using Selenium
Keeps the same browser instance and tab so Discord streams stay connected
Supports windowed/fullscreen toggle, autoplay, and ad blocking
"""

import re
import configparser
import asyncio
import threading
import time
import json
from pathlib import Path


class BrowserManager:
    """Manages a browser controlled via Discord messages using Selenium"""

    # URL pattern: matches http://, https://, or bare domains like youtube.com/xxx
    URL_PATTERN = re.compile(
        r'(?:https?://)?'  # optional http:// or https://
        r'(?:www\.)?'      # optional www.
        r'(?:'             # known domains/shorteners
        r'youtube\.com|youtu\.be|spotify\.com|twitch\.tv|'
        r'google\.com|github\.com|reddit\.com|twitter\.com|x\.com|'
        r'instagram\.com|tiktok\.com|vimeo\.com|dailymotion\.com|'
        r'soundcloud\.com|bandcamp\.com|apple\.com|kick\.com|'
        r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}'  # any domain with TLD
        r')'
        r'(?:/[^\s]*)?'   # optional path
    )

    # JavaScript to auto-play videos and skip ads
    AUTOPLAY_SCRIPT = """
    (function() {
        // Auto-play any HTML5 video element
        function tryAutoplay() {
            document.querySelectorAll('video').forEach(function(v) {
                if (v.paused) {
                    v.play().catch(function(){});
                }
                v.muted = false;
                v.volume = 1.0;
            });
        }

        // Auto-play any HTML5 audio element (podcasts, SoundCloud, etc.)
        function tryAutoplayAudio() {
            document.querySelectorAll('audio').forEach(function(a) {
                if (a.paused) {
                    a.play().catch(function(){});
                }
                a.muted = false;
                a.volume = 1.0;
            });
        }

        // Click play buttons for non-YouTube embedded players
        function clickEmbeddedPlayButtons() {
            var playSelectors = [
                // Vimeo
                '.play-button', '.vp-controls [class*="play"]',
                // Twitch clips / VODs
                '[data-a-target="player-play-button"]',
                // Dailymotion
                '.dm-player-playButton', '.dmp_playBtn',
                // JW Player (button icon)
                '.jw-icon-playback',
                // Video.js
                '.vjs-play-control.vjs-paused',
                // Plyr
                '.plyr__control--overlaid',
                // SoundCloud
                '.playButton', '.sc-button-play',
                // Spotify embed
                '[data-testid="play-pause-button"]', '.encore-play-pause-button',
                // Bandcamp
                '.play-btn',
                // Generic patterns used across many sites
                '[aria-label="Play"]', '[title="Play"]',
                'button[class*="play"]', '[class*="play-btn"]',
                '[class*="playBtn"]', '[class*="PlayButton"]',
                '[class*="play_button"]'
            ];

            playSelectors.forEach(function(sel) {
                try {
                    document.querySelectorAll(sel).forEach(function(btn) {
                        // Only click if it looks like a paused / not-yet-started state
                        var label = (btn.getAttribute('aria-label') || '').toLowerCase();
                        var cls   = (btn.className || '').toLowerCase();
                        var isPaused = label.includes('play') || cls.includes('paused') ||
                                       cls.includes('play') || btn.tagName === 'BUTTON';
                        if (isPaused) { btn.click(); }
                    });
                } catch(e) {}
            });
        }

        // Invoke JS player APIs directly (JW Player, Video.js, Plyr)
        function tryPlayerAPIs() {
            // JW Player — global jwplayer() factory
            if (window.jwplayer) {
                try { jwplayer().play(); } catch(e) {}
                // Also try each instance in case of multiple players
                try {
                    var instances = jwplayer.api ? jwplayer.api.getPlayers() : [];
                    instances.forEach(function(p) { try { p.play(); } catch(e) {} });
                } catch(e) {}
            }

            // Video.js — iterate every .video-js element
            if (window.videojs) {
                document.querySelectorAll('.video-js').forEach(function(el) {
                    try {
                        var player = videojs.getPlayer(el.id || el);
                        if (player && player.paused()) { player.play(); }
                    } catch(e) {}
                });
            }

            // Plyr — try any .plyr container
            if (window.Plyr) {
                document.querySelectorAll('.plyr').forEach(function(el) {
                    try {
                        var p = el._plyr || new Plyr(el);
                        if (p && p.paused) { p.play(); }
                    } catch(e) {}
                });
            }

            // Flowplayer
            if (window.flowplayer) {
                try { flowplayer().play(); } catch(e) {}
            }

            // Vimeo Player API (for pages that use the SDK)
            if (window.Vimeo && window.Vimeo.Player) {
                document.querySelectorAll('iframe[src*="vimeo"]').forEach(function(iframe) {
                    try {
                        var player = new Vimeo.Player(iframe);
                        player.play().catch(function(){});
                    } catch(e) {}
                });
            }
        }

        // Try to reach into same-origin iframes and autoplay their content
        function tryIframeAutoplay() {
            document.querySelectorAll('iframe').forEach(function(iframe) {
                try {
                    var iDoc = iframe.contentDocument || iframe.contentWindow.document;
                    iDoc.querySelectorAll('video, audio').forEach(function(media) {
                        if (media.paused) { media.play().catch(function(){}); }
                        media.muted = false;
                        media.volume = 1.0;
                    });
                } catch(e) {
                    // Cross-origin iframes will throw — ignore silently
                }
            });
        }

        // Dismiss YouTube consent/dialog overlays
        function dismissDialogs() {
            // YouTube consent dialog
            var consentBtn = document.querySelector('button[aria-label*="Reject"], button[aria-label*="Reject all"]');
            if (consentBtn) consentBtn.click();

            // YouTube cookie consent
            var agreeBtn = document.querySelector('[aria-label*="Agree"], [aria-label*="Accept"]');
            if (agreeBtn) agreeBtn.click();

            // Generic dismiss buttons
            var dismissBtns = document.querySelectorAll('[aria-label*="Dismiss"], [aria-label*="Close"]');
            dismissBtns.forEach(function(btn) { btn.click(); });
        }

        // Skip YouTube ads
        function skipAds() {
            // Click "Skip Ad" button
            var skipBtn = document.querySelector('.ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-skip-ad-button');
            if (skipBtn) {
                skipBtn.click();
                console.log('Skipped ad via skip button');
            }

            // Click "Skip" text button
            var skipText = document.querySelector('.ytp-ad-text .ytp-ad-skip-button-text');
            if (skipText) {
                skipText.click();
            }

            // Speed through non-skippable ads
            var adOverlay = document.querySelector('.ytp-ad-player-overlay, .ytp-ad-overlay-container');
            if (adOverlay) {
                var video = document.querySelector('video');
                if (video && !video.paused) {
                    video.playbackRate = 16;
                    video.muted = true;
                    console.log('Speeding through ad at 16x');
                }
            }

            // Close ad overlays/banners
            var adClose = document.querySelector('.ytp-ad-overlay-close-button, .ytp-ad-ui-close-button');
            if (adClose) adClose.click();

            // Remove ad containers
            var adCompanions = document.querySelectorAll('.ytp-ad-companion, .video-ads, .ytp-ad-module');
            adCompanions.forEach(function(el) { el.style.display = 'none'; });
        }

        // Full autoplay sweep: HTML5 media + embedded players + player APIs
        function fullAutoplaySweep() {
            tryAutoplay();
            tryAutoplayAudio();
            clickEmbeddedPlayButtons();
            tryPlayerAPIs();
            tryIframeAutoplay();
            skipAds();
        }

        // Run immediately
        fullAutoplaySweep();
        dismissDialogs();

        // MutationObserver: catch players that load after the initial page render
        // (e.g. lazy-loaded iframes, SPA route changes, dynamic video inserts)
        var _autoplayObserver = new MutationObserver(function(mutations) {
            var hasNewMedia = mutations.some(function(m) {
                return Array.from(m.addedNodes).some(function(node) {
                    if (node.nodeType !== 1) return false;
                    return node.tagName === 'VIDEO' || node.tagName === 'AUDIO' ||
                           node.tagName === 'IFRAME' ||
                           node.querySelector && (
                               node.querySelector('video, audio, iframe') ||
                               node.querySelector('[class*="player"], [class*="Player"]')
                           );
                });
            });
            if (hasNewMedia) {
                setTimeout(fullAutoplaySweep, 500);
            }
        });
        _autoplayObserver.observe(document.body, { childList: true, subtree: true });

        // Periodic polling to catch anything the observer missed
        setInterval(function() {
            tryAutoplay();
            tryAutoplayAudio();
            skipAds();
        }, 1000);

        // Delayed sweeps for slow-loading players (Vimeo, Twitch, etc.)
        setTimeout(function() { fullAutoplaySweep(); dismissDialogs(); }, 2000);
        setTimeout(function() { fullAutoplaySweep(); dismissDialogs(); }, 5000);
        setTimeout(function() { fullAutoplaySweep(); },                  10000);
    })();
    """

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

        # Load bookmarks
        self.bookmarks = self._load_bookmarks()

        print(f"BrowserManager initialized (channel: {self.designated_channel_id})")
        print(f"[Browser] Loaded {len(self.bookmarks)} bookmarks")

    def _ensure_https(self, url):
        """
        Ensure URL has https:// prefix

        Args:
            url: URL string

        Returns:
            str: URL with https:// prefix
        """
        if url.startswith('http://') or url.startswith('https://'):
            return url
        return 'https://' + url

    def _is_valid_url(self, url):
        """
        Check if the URL looks valid (has a dot in the domain)

        Args:
            url: URL string

        Returns:
            bool: True if URL appears valid
        """
        cleaned = url.replace('https://', '').replace('http://', '').replace('www.', '')
        return '.' in cleaned.split('/')[0]

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
            # Re-inject scripts after refresh
            self._inject_scripts_delayed()
            print("Browser refreshed")
            return True
        except Exception as e:
            print(f"Error refreshing browser: {e}")
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
            self.driver = None
            self.current_url = None
            self.is_fullscreen = False
            print("Browser closed")
            return True
        except Exception as e:
            print(f"Error closing browser: {e}")
            self.driver = None
            self.current_url = None
            self.is_fullscreen = False
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
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._navigate_sync, url)

    async def close_browser(self):
        """
        Close the browser instance (async wrapper)

        Returns:
            bool: True if closed successfully
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._close_sync)

    async def refresh_browser(self):
        """
        Refresh the browser page (async wrapper)

        Returns:
            bool: True if refreshed successfully
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._refresh_sync)

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
        """Load bookmarks from JSON file"""
        try:
            if self.bookmarks_file.exists():
                with open(self.bookmarks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[Browser] Error loading bookmarks: {e}")
        return {}

    def _save_bookmarks(self):
        """Save bookmarks to JSON file"""
        try:
            with open(self.bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Browser] Error saving bookmarks: {e}")

    def _add_bookmark(self, name, url):
        """Add a bookmark"""
        name = name.lower().strip()
        self.bookmarks[name] = url
        self._save_bookmarks()
        print(f"[Browser] Bookmark added: {name} -> {url}")

    def _remove_bookmark(self, name):
        """Remove a bookmark"""
        name = name.lower().strip()
        if name in self.bookmarks:
            del self.bookmarks[name]
            self._save_bookmarks()
            print(f"[Browser] Bookmark removed: {name}")
            return True
        return False

    def _resolve_bookmark(self, content):
        """Check if content matches a bookmark name and return the URL"""
        name = content.lower().strip()
        return self.bookmarks.get(name)

    def _has_admin_role(self, user_roles):
        """
        Check if user has the admin role

        Args:
            user_roles: List of Discord role objects

        Returns:
            bool: True if user has admin role
        """
        return any(role.id == self.admin_role_id for role in user_roles)

    def parse_url_with_name(self, content):
        """
        Parse a URL and optional bookmark name from message content.

        Args:
            content: Message content string

        Returns:
            tuple: (url, bookmark_name) where bookmark_name is None if not provided
        """
        content = content.strip()

        # Skip messages that are just commands
        if content.lower() in ('refresh', 'close', 'full', 'max', 'fullscreen', 'min',
                                'bookmarks', 'bm'):
            return None, None

        # Try to find a URL
        match = self.URL_PATTERN.search(content)
        if match:
            url = match.group(0)
            if self._is_valid_url(url):
                url = self._ensure_https(url)
                # Check for bookmark name after the URL
                after_url = content[match.end():].strip()
                bookmark_name = after_url if after_url else None
                return url, bookmark_name

        return None, None

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

        # Check admin role
        if not self._has_admin_role(message.author.roles):
            return False

        content = message.content.strip()
        content_lower = content.lower()

        # Handle 'bookmarks' / 'bm' command - list all bookmarks
        if content_lower in ('bookmarks', 'bm'):
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
            success = await self.close_browser()
            if success:
                await message.add_reaction('✅')
                print("[Browser] Closed browser")
            else:
                await message.add_reaction('❌')
                print("[Browser] No browser to close")
            return True

        # Handle 'full' / 'max' / 'fullscreen' - toggle fullscreen on/off
        if content_lower in ('full', 'max', 'fullscreen'):
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
            if bookmark_name:
                self._add_bookmark(bookmark_name, url)

            if self.driver is not None:
                # Browser already open, navigate same tab to new URL
                success = await self.navigate_browser(url)
                if success:
                    await message.add_reaction('🌐')
                    if bookmark_name:
                        await message.add_reaction('🔖')
                    print(f"[Browser] Navigated to: {url}" + (f" (saved as '{bookmark_name}')" if bookmark_name else ""))
                else:
                    await message.add_reaction('❌')
                    print(f"[Browser] Failed to navigate to: {url}")
            else:
                # No browser open, launch new one
                success = await self.launch_browser(url)
                if success:
                    await message.add_reaction('🌐')
                    if bookmark_name:
                        await message.add_reaction('🔖')
                    print(f"[Browser] Launched browser with: {url}" + (f" (saved as '{bookmark_name}')" if bookmark_name else ""))
                else:
                    await message.add_reaction('❌')
                    print(f"[Browser] Failed to launch browser with: {url}")
            return True

        # Check if the message matches a bookmark name
        bookmark_url = self._resolve_bookmark(content)
        if bookmark_url:
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

    def register_commands(self, bot):
        """Register browser-related commands (no prefix commands needed - raw parsing only)"""
        pass
