/**
 * Automatic Cache-Busting and UI Refresh System
 * Polls the database version endpoint and automatically refreshes the page when data changes
 *
 * Usage: Include this script in any page that displays brand data
 * <script src="/static/js/cache_buster.js"></script>
 */

class CacheBuster {
    constructor(options = {}) {
        this.pollInterval = options.pollInterval || 5000; // Poll every 5 seconds
        this.currentVersion = null;
        this.isPolling = false;
        this.pollTimer = null;
        this.notificationTimeout = null;

        // Configuration
        this.enableNotifications = options.enableNotifications !== false; // Default true
        this.autoRefresh = options.autoRefresh !== false; // Default true
        this.debugMode = options.debugMode || false;

        // Track page visibility to pause polling when hidden
        this.pageVisible = true;

        this.init();
    }

    init() {
        // Get initial database version
        this.getCurrentVersion().then(() => {
            if (this.debugMode) {
                console.log('🔄 Cache Buster initialized with version:', this.currentVersion);
            }
        });

        // Start polling
        this.startPolling();

        // Pause polling when page is hidden
        document.addEventListener('visibilitychange', () => {
            this.pageVisible = !document.hidden;
            if (this.pageVisible) {
                if (this.debugMode) console.log('🔄 Page visible - resuming polling');
                this.startPolling();
            } else {
                if (this.debugMode) console.log('⏸️ Page hidden - pausing polling');
                this.stopPolling();
            }
        });

        // Expose manual refresh function globally
        window.refreshData = () => this.forceRefresh();
    }

    async getCurrentVersion() {
        try {
            const response = await fetch('/api/database_version', {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (this.currentVersion === null) {
                    // First load - just store the version
                    this.currentVersion = data.version;
                } else if (data.version !== this.currentVersion) {
                    // Version changed - data was modified!
                    if (this.debugMode) {
                        console.log('🔄 Database version changed:', {
                            old: this.currentVersion,
                            new: data.version,
                            last_modified: data.last_modified
                        });
                    }
                    this.handleVersionChange(data);
                }
            }
        } catch (error) {
            if (this.debugMode) {
                console.error('❌ Failed to check database version:', error);
            }
        }
    }

    handleVersionChange(versionData) {
        // Show notification to user
        if (this.enableNotifications) {
            this.showUpdateNotification(versionData);
        }

        // Auto-refresh if enabled
        if (this.autoRefresh) {
            setTimeout(() => {
                if (this.debugMode) {
                    console.log('🔄 Auto-refreshing page due to database changes');
                }
                window.location.reload();
            }, 2000); // Give user 2 seconds to see the notification
        }
    }

    showUpdateNotification(versionData) {
        // Remove existing notification if any
        const existingNotification = document.getElementById('cache-buster-notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // Create notification element
        const notification = document.createElement('div');
        notification.id = 'cache-buster-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 14px;
            animation: slideInRight 0.3s ease-out;
        `;

        const lastModified = new Date(versionData.last_modified).toLocaleTimeString();

        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="font-size: 24px;">🔄</div>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Data Updated</div>
                    <div style="font-size: 12px; opacity: 0.9;">
                        Database modified at ${lastModified}
                        ${this.autoRefresh ? ' • Refreshing...' : ' • Click to refresh'}
                    </div>
                </div>
            </div>
        `;

        // Add click handler for manual refresh
        if (!this.autoRefresh) {
            notification.style.cursor = 'pointer';
            notification.addEventListener('click', () => {
                window.location.reload();
            });
        }

        // Add animation keyframes
        if (!document.getElementById('cache-buster-styles')) {
            const style = document.createElement('style');
            style.id = 'cache-buster-styles';
            style.textContent = `
                @keyframes slideInRight {
                    from {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes fadeOut {
                    from {
                        opacity: 1;
                    }
                    to {
                        opacity: 0;
                        transform: translateX(400px);
                    }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(notification);

        // Auto-remove notification after refresh or timeout
        this.notificationTimeout = setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 10000);
    }

    startPolling() {
        if (this.isPolling) return;

        this.isPolling = true;
        this.pollTimer = setInterval(() => {
            if (this.pageVisible) {
                this.getCurrentVersion();
            }
        }, this.pollInterval);

        if (this.debugMode) {
            console.log(`🔄 Polling started (every ${this.pollInterval/1000}s)`);
        }
    }

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
            this.isPolling = false;
        }
    }

    forceRefresh() {
        if (this.debugMode) {
            console.log('🔄 Force refreshing page');
        }
        window.location.reload();
    }

    destroy() {
        this.stopPolling();
        if (this.notificationTimeout) {
            clearTimeout(this.notificationTimeout);
        }
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Check if cache busting is enabled (can be disabled per-page)
        if (window.DISABLE_CACHE_BUSTER !== true) {
            window.cacheBuster = new CacheBuster({
                pollInterval: window.CACHE_BUSTER_POLL_INTERVAL || 5000,
                enableNotifications: window.CACHE_BUSTER_NOTIFICATIONS !== false,
                autoRefresh: window.CACHE_BUSTER_AUTO_REFRESH !== false,
                debugMode: window.CACHE_BUSTER_DEBUG || false
            });
        }
    });
} else {
    // DOM already loaded
    if (window.DISABLE_CACHE_BUSTER !== true) {
        window.cacheBuster = new CacheBuster({
            pollInterval: window.CACHE_BUSTER_POLL_INTERVAL || 5000,
            enableNotifications: window.CACHE_BUSTER_NOTIFICATIONS !== false,
            autoRefresh: window.CACHE_BUSTER_AUTO_REFRESH !== false,
            debugMode: window.CACHE_BUSTER_DEBUG || false
        });
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CacheBuster;
}
