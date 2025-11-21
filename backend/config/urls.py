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
    urlpatterns += [re_path(
        r"^media/patients/files/(?P<id>\d+)\.pdf$",
        ProtectedMediaView.as_view(),
        name="protected_media",
    )]

    urlpatterns+= static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
