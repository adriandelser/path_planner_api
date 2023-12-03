from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import UserManager
from django.db import models
from model_utils.models import UUIDModel, TimeStampedModel

from accounts.config.settings import app_name
from django_extras.models_utils import UpdatableMixin


class ExtendedUserQuerySet(models.QuerySet):
    ...


class ExtendedUserManager(UserManager):
    ...


class User(UUIDModel, TimeStampedModel, AbstractBaseUser, UpdatableMixin):
    class Meta:
        app_label = app_name

    username = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        unique=True,
        help_text="The users cognito username",
    )
    first_name = models.CharField(max_length=100, help_text="Users first name")
    last_name = models.CharField(max_length=100, help_text="Users last name")
    full_name = models.CharField(
        null=True,
        max_length=201,
        editable=False,
        help_text=("Users full name (diacritics removed and populated automatially)"),
    )
    email = models.EmailField(
        null=True,
        blank=True,
        help_text=("Hi"),
    )
    phone_number = models.CharField(
        null=True, blank=True, max_length=50, help_text="Users phone number"
    )
    professional_title = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        help_text="The users professional title",
    )
    # Django user model attributes
    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = ExtendedUserManager()

    ...
