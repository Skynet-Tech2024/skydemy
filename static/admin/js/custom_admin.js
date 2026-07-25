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
// ============================================
// TURN CHECKBOXES INTO TOGGLE SWITCHES
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[type="checkbox"]').forEach(function(checkbox) {
        // Skip if already processed or if it's a select-all checkbox
        if (checkbox.closest('.toggle-switch') || checkbox.id === 'action-toggle' || checkbox.id === 'select-all') {
            return;
        }

        // Build toggle structure
        var wrapper = document.createElement('span');
        wrapper.className = 'toggle-switch';

        var slider = document.createElement('span');
        slider.className = 'slider';

        // Move the checkbox inside the wrapper
        checkbox.parentNode.insertBefore(wrapper, checkbox);
        wrapper.appendChild(checkbox);
        wrapper.appendChild(slider);

        // Add container for better alignment
        var container = document.createElement('div');
        container.className = 'toggle-container';
        checkbox.parentNode.insertBefore(container, wrapper);
        container.appendChild(wrapper);

        // Move any help text or label into the container
        var next = wrapper.nextElementSibling;
        if (next && (next.classList.contains('help') || next.classList.contains('help-text'))) {
            container.appendChild(next);
        }

        // Wrap the label around the toggle
        var label = container.closest('.field-box')?.querySelector('label');
        if (label) {
            var labelText = label.textContent.trim();
            // If the label is still attached to the checkbox, we'll duplicate it inside the container
            // but keep the checkbox's label for accessibility
            var labelSpan = document.createElement('span');
            labelSpan.textContent = labelText;
            labelSpan.style.marginLeft = '0px';
            // Move the label text into the container (but keep the original label for form submission)
            // We'll just add a visual label next to the toggle
            if (!container.querySelector('label')) {
                var newLabel = document.createElement('label');
                newLabel.textContent = labelText;
                newLabel.style.display = 'inline-block';
                newLabel.style.fontWeight = '500';
                newLabel.style.cursor = 'pointer';
                container.insertBefore(newLabel, wrapper);
            }
        }
    });
});