from django.contrib.auth.models import Permission
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from . import models


class UserSerializer(
    ModelSerializer,
):
    name = serializers.CharField(source="full_name")

    class Meta:
        model = models.User
        fields = ("id", "name", "full_name", "avatar", "email", "type", "self")



class PermissionSerializer(serializers.ModelSerializer):
    model = serializers.CharField(source="content_type.model")

    class Meta:
        model = Permission
        fields = (
            "id",
            "name",
            "description",
            "model",
        )

