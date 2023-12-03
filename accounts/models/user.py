class User(
    models_utils.UUIDModel,
    models_utils.CreatedByModel,
    models_utils.TimeStampedModel,
    auth.models.AbstractBaseUser,
    django_extras.models_utils.UpdateableMixin
):
    ...
