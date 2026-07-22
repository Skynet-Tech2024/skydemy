from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import RegisterForm, ProfileCompletionForm
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
                # Store role and phone in session for Step 2
                request.session['temp_user_id'] = user.id
                request.session['temp_role'] = role
                request.session['temp_phone'] = phone_number

                print(f"🟢 User created: {username}, ID: {user.id}")

                # Redirect to Step 2 (profile completion)
                return redirect('complete_profile')

            except Exception as e:
                print(f"❌ Error creating user: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, "We couldn't create your account. Please try again.")
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
    role = request.session.get('temp_role', 'learner')

    # Check if profile already exists
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile(user=user)

    if request.method == 'POST':
        form = ProfileCompletionForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = user
            profile.role = role
            profile.whatsapp_number = request.session.get('temp_phone', '')
            if not profile.verification_status:
                profile.verification_status = 'pending'
            profile.save()
            print(f"🟢 Profile completed for {user.username}")

            # Clear session data
            del request.session['temp_user_id']
            del request.session['temp_role']
            if 'temp_phone' in request.session:
                del request.session['temp_phone']

            messages.success(
                request,
                "✅ Your account has been created and is now pending review by our admin team. "
                "You can now log in."
            )
            return redirect('login')
        else:
            print("❌ Profile form invalid:")
            print(form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProfileCompletionForm(instance=profile, initial={'role': role})

    return render(request, 'users/complete_profile.html', {
        'form': form,
        'user': user,
        'role': role
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