from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def login_and_verification_required(allowed_statuses):
    """
    General decorator: user must be logged in and have one of the allowed statuses.
    allowed_statuses: list of statuses ('pending','approved','verified')
    Rejected users are always blocked.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please login first.")
                return redirect('login')

            profile = request.user.profile
            status = profile.verification_status

            # Rejected users are banned entirely
            if status == 'rejected':
                messages.error(request, "Your account has been rejected. Contact support for assistance.")
                return redirect('home')

            # Check if the user's status is allowed
            if status not in allowed_statuses:
                # If pending, give a special message
                if status == 'pending':
                    messages.warning(request, "Your account is pending approval. You have limited access.")
                else:
                    messages.warning(request, "You do not have permission for this action.")
                return redirect('profile')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# ===== Specific shortcuts =====

def basic_access(view_func):
    """For pages accessible to all logged-in users (pending, approved, verified)"""
    return login_and_verification_required(['pending', 'approved', 'verified'])(view_func)

def lesson_access(view_func):
    """For accessing lessons (approved and verified only)"""
    return login_and_verification_required(['approved', 'verified'])(view_func)

def upload_access(view_func):
    """For uploading lessons/exams (approved and verified) - same as lesson_access"""
    return login_and_verification_required(['approved', 'verified'])(view_func)

def video_lesson_access(view_func):
    """For accessing or uploading video lessons (verified only)"""
    return login_and_verification_required(['verified'])(view_func)

def profile_access(view_func):
    """For profile pages (all logged-in users except rejected) - uses basic_access"""
    return basic_access(view_func)