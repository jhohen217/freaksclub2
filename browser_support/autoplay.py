"""Autoplay/ad-skip JavaScript injected into browser pages."""

AUTOPLAY_SCRIPT = r"""
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
