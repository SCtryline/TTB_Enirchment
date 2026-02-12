document.addEventListener('DOMContentLoaded', function() {
    loadHomeStats();
});

async function loadHomeStats() {
    try {
        const response = await fetch('/get_database_stats');
        const data = await response.json();

        const totalBrands = data.total_brands || 0;
        const totalSkus = data.total_skus || 0;
        const totalImporters = data.total_importers || 0;
        const enriched = data.brands_with_websites || 0;
        const needUrl = totalBrands - enriched;

        // Animate stat tiles
        animateCounter('stat-brands', totalBrands);
        animateCounter('stat-skus', totalSkus);
        animateCounter('stat-importers', totalImporters);
        animateCounter('stat-enriched', enriched);
        animateCounter('stat-need-url', needUrl);

        // Enrichment progress bar
        const pct = totalBrands > 0 ? Math.round((enriched / totalBrands) * 100) : 0;
        const bar = document.getElementById('enrichment-bar');
        const pctEl = document.getElementById('enrichment-pct');
        const textEl = document.getElementById('enrichment-text');

        if (bar) {
            // Small delay so the CSS transition is visible
            requestAnimationFrame(function() {
                bar.style.width = pct + '%';
            });
        }
        if (pctEl) pctEl.textContent = pct + '%';
        if (textEl) textEl.textContent = enriched.toLocaleString() + ' of ' + totalBrands.toLocaleString() + ' brands have a website';

    } catch (error) {
        console.error('Error loading home stats:', error);
        ['stat-brands', 'stat-skus', 'stat-importers', 'stat-enriched', 'stat-need-url'].forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.textContent = '0';
        });
    }
}

function animateCounter(elementId, targetValue) {
    var element = document.getElementById(elementId);
    if (!element) return;

    var duration = 1200;
    var startTime = performance.now();

    function update(currentTime) {
        var elapsed = currentTime - startTime;
        var progress = Math.min(elapsed / duration, 1);
        // Ease-out cubic
        var eased = 1 - Math.pow(1 - progress, 3);
        element.textContent = Math.floor(targetValue * eased).toLocaleString();
        if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
}