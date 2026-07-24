from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import RegisterStep1Form
from .models import UserProfile

# ===== STEP 1: Account Creation =====
def register(request):
    print("🔵 Registration view called (Step 1)")
    if request.method == 'POST':
        print("🟡 POST request received")
        form = RegisterStep1Form(request.POST)
        if form.is_valid():
            try:
                # Create the user (form saves only User, not profile)
                user = form.save()

                # Now update the profile
                profile = user.profile
                profile.full_name = form.cleaned_data['full_name']
                profile.role = 'learner'
                profile.verification_status = 'pending'
                profile.save()

                # Store user ID in session for Step 2
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

    if request.method == 'POST':
        # Collect profile fields
        level = request.POST.get('level')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        role = request.POST.get('role')
        school_name = request.POST.get('school_name', '')

        # Validate required fields
        if not level:
            messages.error(request, "Education level is required.")
            return render(request, 'users/complete_profile.html', {
                'user': user,
                'profile': profile,
                'level_choices': UserProfile.LEVEL_CHOICES,
                'role_choices': UserProfile.ROLE_CHOICES,
            })
        if not phone_number:
            messages.error(request, "Phone number is required.")
            return render(request, 'users/complete_profile.html', {
                'user': user,
                'profile': profile,
                'level_choices': UserProfile.LEVEL_CHOICES,
                'role_choices': UserProfile.ROLE_CHOICES,
            })
        if not address:
            messages.error(request, "Address is required.")
            return render(request, 'users/complete_profile.html', {
                'user': user,
                'profile': profile,
                'level_choices': UserProfile.LEVEL_CHOICES,
                'role_choices': UserProfile.ROLE_CHOICES,
            })
        if not role:
            messages.error(request, "Role is required.")
            return render(request, 'users/complete_profile.html', {
                'user': user,
                'profile': profile,
                'level_choices': UserProfile.LEVEL_CHOICES,
                'role_choices': UserProfile.ROLE_CHOICES,
            })
        
        if role == 'learner' and not school_name:
            messages.error(request, "School name is required for learners.")
            return render(request, 'users/complete_profile.html', {
                'user': user,
                'profile': profile,
                'level_choices': UserProfile.LEVEL_CHOICES,
                'role_choices': UserProfile.ROLE_CHOICES,
            })

        # Update profile
        profile.level = level
        profile.phone_number = phone_number
        profile.address = address
        profile.role = role
        # Uncomment if you have school_name field:
        # profile.school_name = school_name
        profile.save()

        # Clear session and log in the user
        del request.session['temp_user_id']
        login(request, user)

        messages.success(request, "✅ Registration complete! Welcome to SKYDEMY.")
        return redirect('dashboard')

    level_choices = UserProfile.LEVEL_CHOICES
    role_choices = UserProfile.ROLE_CHOICES
    return render(request, 'users/complete_profile.html', {
        'user': user,
        'profile': profile,
        'level_choices': level_choices,
        'role_choices': role_choices,
    })


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