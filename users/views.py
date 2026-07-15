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
                user = form.save()
                print(f"🟢 User saved: {user.username}")
                login(request, user)
                print("🟢 User logged in")
                return redirect('home')
            except Exception as e:
                print(f"❌ Exception during save/login: {e}")
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