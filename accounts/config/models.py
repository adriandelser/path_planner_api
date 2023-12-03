from django_extras import ClassRef

app_name = "accounts"

# Local models
prepend_model = f"{app_name}.models."


MODEL_USER = ClassRef(f"{prepend_model}.User")
MODEL_PERMISSION = ClassRef("auth.Permission", django_native=True)
MODEL_CONTENT_TYPE = ClassRef("contenttypes.ContentType", django_native=True)
MODEL_GROUP = ClassRef("auth.Group", django_native=True)
