from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse

from .forms import RegisterStep1Form
from .models import UserProfile, Level
from core.constants import LEVEL_CHOICES
from datetime import datetime


# ===== STEP 1: Account Creation =====
def register(request):
    print("🔵 Registration view called (Step 1)")
    if request.method == 'POST':
        print("🟡 POST request received")
        form = RegisterStep1Form(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'full_name': form.cleaned_data['full_name'],
                        'role': 'learner',
                        'verification_status': 'pending'
                    }
                )
                if not created:
                    profile.full_name = form.cleaned_data['full_name']
                    profile.role = 'learner'
                    profile.verification_status = 'pending'
                    profile.save()

                request.session['temp_user_id'] = user.id
                print(f"🟢 User and profile created: {user.username}, ID: {user.id}")
                messages.success(request, "✅ Account created! Please complete your profile.")
                return redirect('/users/complete-profile/')

            except Exception as e:
                print(f"❌ Error creating user: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"We couldn't create your account: {str(e)}")
        else:
            print("❌ Form invalid:")
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterStep1Form()

    return render(request, 'users/register.html', {'form': form})


# ===== STEP 2: Profile Completion (UPDATED for multiple levels) =====
def complete_profile(request):
    print("🔵 Profile completion view called (Step 2)")
    user_id = request.session.get('temp_user_id')
    if not user_id:
        messages.error(request, "Please create your account first.")
        return redirect('register')

    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    allowed_roles = [choice for choice in UserProfile.ROLE_CHOICES if choice[0] != 'admin']

    # Get all Level objects for the template
    all_levels = Level.objects.all()

    if request.method == 'POST':
        # Get selected level codes from POST (list of codes)
        selected_level_codes = request.POST.getlist('levels')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        role = request.POST.get('role')
        school_name = request.POST.get('school_name', '')

        if phone_number == '':
            phone_number = None
        if address == '':
            address = None

        if not selected_level_codes:
            messages.error(request, "Please select at least one education level.")
            return render(request, 'users/complete_profile.html', {
                'user': user, 'profile': profile,
                'all_levels': all_levels, 'role_choices': allowed_roles,
            })

        if not role:
            messages.error(request, "Role is required.")
            return render(request, 'users/complete_profile.html', {
                'user': user, 'profile': profile,
                'all_levels': all_levels, 'role_choices': allowed_roles,
            })

        if role == 'admin':
            messages.error(request, "Invalid role selection.")
            return render(request, 'users/complete_profile.html', {
                'user': user, 'profile': profile,
                'all_levels': all_levels, 'role_choices': allowed_roles,
            })

        if role == 'learner' and not school_name:
            messages.error(request, "School name is required for learners.")
            return render(request, 'users/complete_profile.html', {
                'user': user, 'profile': profile,
                'all_levels': all_levels, 'role_choices': allowed_roles,
            })

        # Set the many-to-many levels
        level_objects = Level.objects.filter(code__in=selected_level_codes)
        profile.levels.set(level_objects)

        # Update other fields
        profile.phone_number = phone_number
        # profile.address = address  # uncomment if you have this field in the model
        profile.role = role
        profile.save()

        # Clear session and redirect
        del request.session['temp_user_id']
        request.session['reg_user_id'] = user.id

        messages.success(request, "✅ Registration complete! Redirecting to success page.")
        return redirect('/users/registration-success/')

    return render(request, 'users/complete_profile.html', {
        'user': user, 'profile': profile,
        'all_levels': all_levels, 'role_choices': allowed_roles,
    })


# ===== REGISTRATION SUCCESS =====
def registration_success(request):
    user_id = request.session.get('reg_user_id')
    if not user_id:
        return redirect('register')
    user = get_object_or_404(User, id=user_id)
    del request.session['reg_user_id']
    context = {
        'user': user,
        'submitted_at': user.date_joined,
        'profile': user.profile,
    }
    return render(request, 'users/registration_success.html', context)


# ===== PENDING APPROVAL =====
def pending_approval(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.profile.verification_status in ['approved', 'verified']:
        return redirect('dashboard')
    return render(request, 'users/pending_approval.html')


# ===== Login =====
def custom_login(request):
    print("🔵 Login view called")
    if request.method == 'POST':
        print("🟡 POST request received")
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"🟡 Username: {username}")
        user = authenticate(request, username=username, password=password)
        print(f"🟢 Authenticated user: {user}")
        if user is not None:
            # Check for soft‑deleted account
            if hasattr(user, 'profile') and hasattr(user.profile, 'is_deleted') and user.profile.is_deleted:
                messages.error(request, "Your account has been deactivated. Please contact support.")
                return redirect('account_deactivated')
            # Approval check
            if user.profile.verification_status not in ['approved', 'verified']:
                return redirect('pending_approval')
            else:
                login(request, user)
                print("✅ Login successful, session key:", request.session.session_key)
                return redirect('dashboard')
        else:
            print("❌ Login failed")
            messages.error(request, 'Invalid username or password.')
    return render(request, 'users/login.html')


def custom_logout(request):
    auth_logout(request)
    return redirect('login')


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return 'dashboard'


def account_deactivated(request):
    return render(request, 'users/account_deactivated.html')


# ===== CUSTOM ADMIN LEVEL LIST =====
@staff_member_required
def admin_level_list(request):
    levels = Level.objects.all().order_by('code')

    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        levels = levels.filter(
            Q(code__icontains=search_query) |
            Q(name__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(levels, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Build rows for the template
    level_rows = []
    for i, level in enumerate(page_obj, start=page_obj.start_index()):  # <-- FIXED: call method
        level_rows.append({
            'cells': [
                f'<input type="checkbox" name="selected_items" value="{level.id}">',
                str(i),
                f'<strong>{level.code}</strong>',
                level.name,
                '—'
            ]
        })

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_items')
        if selected_ids:
            if action == 'delete':
                Level.objects.filter(id__in=selected_ids).delete()
                messages.success(request, f"{len(selected_ids)} level(s) deleted.")
            else:
                messages.error(request, "Invalid action.")
        else:
            messages.error(request, "No levels selected.")
        return redirect('admin:level_list')

    context = {
        'level_rows': level_rows,
        'total': levels.count(),
        'page_obj': page_obj,
        'paginator': paginator,
        'search_query': search_query,
    }
    return render(request, 'admin/users/level_list.html', context)