from django.contrib.auth.models import Permission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from django_extras.mixins import OptimizedQuerySetAnnotationsMixin
from . import filters, models, serializers


class UserViewSet(
    OptimizedQuerySetAnnotationsMixin,
    viewsets.ModelViewSet,
):
    """
    View endpoints for the creation and management of users.

    """

    client_relation_field = "clients"
    is_owner_check_attributes = [("self", "id")]

    queryset = models.User.objects.all()
    serializer_class = serializers.UserSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.UsersFilterSet
    score_keys = []
    score_ordering = []


class PermissionViewSet(
    OptimizedQuerySetAnnotationsMixin,
    viewsets.ModelViewSet,
):
    """
    List view to retrieve permissions.

    """

    queryset = Permission.objects.all()
    serializer_class = serializers.PermissionSerializer
