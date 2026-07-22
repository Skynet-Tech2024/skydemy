from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import RegisterForm  # Only RegisterForm, no ProfileCompletionForm
from .models import UserProfile

# ===== STEP 1: Account Creation =====
def register(request):
    print("🔵 Registration view called (Step 1)")
    if request.method == 'POST':
        print("🟡 POST request received")
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                # Create user
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                phone_number = form.cleaned_data.get('phone_number', '')
                role = form.cleaned_data['role']

                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=phone_number  # Use phone as email for recovery
                )

                # Create or get the profile to avoid duplicate constraint errors
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'role': role,
                        'verification_status': 'pending'
                    }
                )
                # If the profile already existed, update its role and status
                if not created:
                    profile.role = role
                    profile.verification_status = 'pending'
                    profile.save()

                # Store user ID in session for Step 2
                request.session['temp_user_id'] = user.id

                print(f"🟢 User and profile created/updated: {username}, ID: {user.id}")

                messages.success(request, "Account created! Please complete your profile.")
                return redirect('complete_profile')

            except Exception as e:
                print(f"❌ Error creating user: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"We couldn't create your account: {str(e)}")
        else:
            print("❌ Form invalid:")
            print(form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


# ===== STEP 2: Profile Completion (optional) =====
def complete_profile(request):
    print("🔵 Profile completion view called (Step 2)")
    user_id = request.session.get('temp_user_id')
    if not user_id:
        messages.error(request, "Please create your account first.")
        return redirect('register')

    user = get_object_or_404(User, id=user_id)
    profile = user.profile  # Should exist from registration

    if request.method == 'POST':
        # Collect optional profile fields manually
        level = request.POST.get('level')
        whatsapp_number = request.POST.get('whatsapp_number')
        avatar = request.FILES.get('avatar')

        if level:
            profile.level = level
        if whatsapp_number:
            profile.whatsapp_number = whatsapp_number
        if avatar:
            profile.avatar = avatar
        profile.save()

        # Clear session data
        del request.session['temp_user_id']

        messages.success(
            request,
            "✅ Your profile is complete! Your account is pending review. You can now log in."
        )
        return redirect('login')

    # GET request - show profile completion form
    level_choices = UserProfile.LEVEL_CHOICES
    return render(request, 'users/complete_profile.html', {
        'user': user,
        'profile': profile,
        'level_choices': level_choices,
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