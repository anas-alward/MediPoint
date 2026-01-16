from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.conf import settings
from apps.patients.views import ProtectedMediaView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('config.api_route')) 
]


if settings.DEBUG:
    

    urlpatterns+= static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    