// Toggle profile dropdown
document.addEventListener('DOMContentLoaded', function() {
    const avatar = document.querySelector('.profile-dropdown .avatar');
    const dropdown = document.querySelector('.profile-dropdown .dropdown-menu');
    if (avatar && dropdown) {
        avatar.addEventListener('click', function(e) {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });
        document.addEventListener('click', function() {
            dropdown.classList.remove('show');
        });
    }
});
// ===== Smooth page transitions (optional) =====
document.addEventListener('DOMContentLoaded', function() {
    // Fade in the main content
    const content = document.querySelector('#content');
    if (content) {
        content.style.opacity = '0';
        content.style.transition = 'opacity 0.4s ease';
        setTimeout(() => {
            content.style.opacity = '1';
        }, 100);
    }

    // Add a subtle hover effect to all buttons
    document.querySelectorAll('.button, input[type="submit"], a.button').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});