import model_utils
from model_utils.models import UUIDModel, TimeStampedModel
from django.db import models

from django_extras.models_utils import UpdatableMixin
from django.contrib.auth.models import UserManager, AbstractUser

from accounts.config.settings import app_name

class ExtendedUserQuerySet(models.QuerySet):
    ...
class ExtendedUserManager(UserManager):
    ...
class User(
    UUIDModel,
    TimeStampedModel,
    AbstractUser,
    UpdatableMixin
):
    class Meta:
        app_label = app_name


    email = models.EmailField(
        null=True,
        blank=True,
        help_text=(
            "Email address"
        ),
    )
    # Django user model attributes
    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = ExtendedUserManager()
    ...
