from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('core.urls')),
]

handler400 = 'core.views.custom_bad_request'
handler403 = 'core.views.custom_permission_denied'
handler404 = 'core.views.custom_page_not_found'
handler500 = 'core.views.custom_server_error'


if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )