from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import HttpResponse
from .forms import RegisterForm

def register(request):
    import traceback
    print("🔵 Registration view called")
    if request.method == 'POST':
        print("🟡 POST request received")
        try:
            form = RegisterForm(request.POST, request.FILES)
            print("🟡 Form created")
            if form.is_valid():
                print("🟢 Form is valid")
                user = form.save()
                print("🟢 User saved:", user.username)
                login(request, user)
                print("🟢 User logged in")
                return redirect('home')
            else:
                print("❌ Form invalid:", form.errors)
                print("❌ Non-field errors:", form.non_field_errors())
        except Exception as e:
            print("❌ Exception during registration:", str(e))
            print(traceback.format_exc())
            messages.error(request, "An error occurred during registration. Please try again.")
            # Recreate the form with POST data to show errors
            form = RegisterForm(request.POST, request.FILES)
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})def custom_login(request):
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
        return '/'