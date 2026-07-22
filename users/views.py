from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from .forms import RegisterForm

def register(request):
    print("🔵 Registration view called")
    if request.method == 'POST':
        print("🟡 POST request received")
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save the user but do NOT log them in
                user = form.save(commit=False)
                # Mark account inactive until admin approval
                user.is_active = False
                user.save()
                print(f"🟢 User saved: {user.username}")

                # Set profile verification status to 'pending'
                try:
                    profile = user.profile
                    profile.verification_status = 'pending'
                    profile.save()
                    print(f"🟢 Profile verification set to pending for {user.username}")
                except Exception as e:
                    print(f"⚠️ Could not set profile pending: {e}")

                messages.success(
                    request,
                    "✅ Your account has been created and is now pending review by our admin team. "
                    "You will receive an email once your account is approved. "
                    "Thank you for your patience! Review typically takes 24–48 hours."
                )

                return redirect('login')

            except Exception as e:
                print(f"❌ Exception during save: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"An error occurred: {e}")
        else:
            print("❌ Form invalid:")
            print(form.errors)
            print(form.non_field_errors())
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


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
            # Check if user is active
            if not user.is_active:
                print("❌ User account is inactive")
                messages.error(request, 'Your account is pending admin approval. Please wait for the verification email.')
                return render(request, 'users/login.html')
            login(request, user)
            print("✅ Login successful, session key:", request.session.session_key)
            return redirect('/admin/')
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
        return '/'