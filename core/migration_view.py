@"
from django.http import HttpResponse
from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def run_migrations(request):
    try:
        call_command('migrate', interactive=False)
        return HttpResponse("Migrations completed successfully!")
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")
"@ | Out-File -FilePath core\migration_view.py -Encoding utf8