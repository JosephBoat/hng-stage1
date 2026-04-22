import os
import django
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

application = get_wsgi_application()

# Vercel expects a variable named "app"
app = application
