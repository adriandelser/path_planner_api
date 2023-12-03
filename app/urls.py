from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

import rest_framework.exceptions
from rest_framework import routers


import accounts.urls

# API urls
router = routers.SimpleRouter(trailing_slash=False)

# handler404 = views.not_found

api_title = settings.PROJECT_NAME
api_description = settings.PROJECT_DESCRIPTION

handler500 = rest_framework.exceptions.server_error
handler400 = rest_framework.exceptions.bad_request

urlpatterns = [
    path("", include(accounts.urls)),
]

if settings.PROFILE_REQUESTS:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

if settings.SHOW_SWAGGER_DOCS:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )

    urlpatterns = [
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "swagger/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger",
        ),
        path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ] + urlpatterns

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.SHOW_DJANGO_TOOLBAR:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

urlpatterns += router.urls

if settings.URL_PREFIX:
    urlpatterns = [path(f"{settings.URL_PREFIX}/", include(urlpatterns))]
