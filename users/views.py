from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from .forms import RegisterForm
from .models import UserProfile

def register(request):
    print("🔵 Registration view called")
    if request.method == 'POST':
        print("🟡 POST request received")
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save the user but DO NOT commit yet
                user = form.save(commit=False)
                # Keep account active; use verification_status for permissions
                user.is_active = True
                user.save()  # Now save the user
                print(f"🟢 User saved: {user.username}")

                # Now create the UserProfile manually
                profile = UserProfile.objects.create(
                    user=user,
                    role=form.cleaned_data['role'],
                    level=form.cleaned_data['level'],
                    whatsapp_number=form.cleaned_data.get('whatsapp_number', ''),
                    avatar=form.cleaned_data.get('avatar'),
                    verification_status='pending',
                    # Identity fields (if any)
                    id_document=form.cleaned_data.get('id_document'),
                    id_document_type=form.cleaned_data.get('id_document_type'),
                    utility_bill=form.cleaned_data.get('utility_bill'),
                    location_verified=False,
                )
                print(f"🟢 Profile created for {user.username}")

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
            # Allow login regardless of is_active (we use verification_status for permissions)
            login(request, user)
            print("✅ Login successful, session key:", request.session.session_key)
            # Redirect to dashboard after login
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
        # Redirect to dashboard after login
        return 'dashboard'