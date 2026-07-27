from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import RegisterStep1Form
from .models import UserProfile
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


# ===== STEP 2: Profile Completion =====
def complete_profile(request):
    print("🔵 Profile completion view called (Step 2)")
    user_id = request.session.get('temp_user_id')
    if not user_id:
        messages.error(request, "Please create your account first.")
        return redirect('register')

    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    allowed_roles = [choice for choice in UserProfile.ROLE_CHOICES if choice[0] != 'admin']

    if request.method == 'POST':
               # Collect profile fields
        level = request.POST.get('level')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        role = request.POST.get('role')
        school_name = request.POST.get('school_name', '')

        # Convert empty strings to None to avoid unique constraint violations
        if phone_number == '':
            phone_number = None
        if address == '':
            address = None

        if not level:
            messages.error(request, "Education level is required.")
            return render(request, 'users/complete_profile.html', {
                'user': user, 'profile': profile,
                'level_choices': LEVEL_CHOICES, 'role_choices': allowed_roles,
            })
        if not role:
            messages.error(request, "Role is required.")
            return render(request, 'users/complete_profile.html', {
                'user': user, 'profile': profile,
                'level_choices': LEVEL_CHOICES, 'role_choices': allowed_roles,
            })
        if role == 'admin':
            messages.error(request, "Invalid role selection.")
            return render(request, 'users/complete_profile.html', {
                'user': user, 'profile': profile,
                'level_choices': LEVEL_CHOICES, 'role_choices': allowed_roles,
            })
        if role == 'learner' and not school_name:
            messages.error(request, "School name is required for learners.")
            return render(request, 'users/complete_profile.html', {
                'user': user, 'profile': profile,
                'level_choices': LEVEL_CHOICES, 'role_choices': allowed_roles,
            })

        # Update profile
        profile.level = level
        profile.phone_number = phone_number
        profile.address = address
        profile.role = role
        profile.save()

        # Clear temp session and store user ID for success page
        del request.session['temp_user_id']
        request.session['reg_user_id'] = user.id

        messages.success(request, "✅ Registration complete! Redirecting to success page.")
        return redirect('registration_success')

    # GET request
    return render(request, 'users/complete_profile.html', {
        'user': user, 'profile': profile,
        'level_choices': LEVEL_CHOICES, 'role_choices': allowed_roles,
    })


# ===== REGISTRATION SUCCESS =====
def registration_success(request):
    user_id = request.session.get('reg_user_id')
    if not user_id:
        return redirect('register')
    user = get_object_or_404(User, id=user_id)
    # Clear the session variable after retrieving
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
    # If user is already approved, redirect to dashboard
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
            login(request, user)
            print("✅ Login successful, session key:", request.session.session_key)
            # Check if user is approved
            if user.profile.verification_status not in ['approved', 'verified']:
                return redirect('pending_approval')
            else:
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