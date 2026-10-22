/**
 * LogGuard - General Application Interactions
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Auto-dismiss flash alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });

    // 2. Refresh Lucide icons if dynamically loaded
    if (window.lucide) {
        lucide.createIcons();
    }
});
