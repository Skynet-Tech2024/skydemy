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