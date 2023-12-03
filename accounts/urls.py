from django.urls import include, path
from rest_framework_nested import routers

from . import views

router = routers.SimpleRouter(trailing_slash=False)
router.register("users", views.UserViewSet)
router.register("permissions", views.PermissionViewSet)
user_router = routers.NestedSimpleRouter(
    router, "users", lookup="user", trailing_slash=False
)

# nested_root_user_views = NestedAndRootPathRouter(
#     router, "users", lookup="user", trailing_slash=False
# )
# user_group_router = routers.NestedSimpleRouter(
#     router, "user-groups", lookup="group", trailing_slash=False
# )

urlpatterns = [
    path("", include(router.urls)),
    path("", include(user_router.urls)),
]
