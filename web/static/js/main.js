document.addEventListener('DOMContentLoaded', function() {
    // Load dashboard stats for home page hero section
    loadDashboardStats();
});

// Load dashboard statistics for the hero section
async function loadDashboardStats() {
    try {
        const response = await fetch('/get_database_stats');
        const data = await response.json();
        
        // Animate counters with data
        animateCounter('total-brands-hero', data.total_brands || 0);
        animateCounter('total-skus-hero', data.total_skus || 0);
        animateCounter('total-importers-hero', data.total_importers || 0);
        
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        // Fallback to 0 if there's an error
        document.getElementById('total-brands-hero').textContent = '0';
        document.getElementById('total-skus-hero').textContent = '0';
        document.getElementById('total-importers-hero').textContent = '0';
    }
}

// Animate counter with easing effect
function animateCounter(elementId, targetValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const startValue = 0;
    const duration = 2000; // 2 seconds
    const startTime = performance.now();
    
    function updateCounter(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Ease out cubic for smooth animation
        const easedProgress = 1 - Math.pow(1 - progress, 3);
        const currentValue = Math.floor(startValue + (targetValue - startValue) * easedProgress);
        
        element.textContent = currentValue.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(updateCounter);
        }
    }
    
    requestAnimationFrame(updateCounter);
}