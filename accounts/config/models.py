from django_extras import ClassRef

app_name = "users"

# Local models
prepend_model = f"{app_name}.models."

MODEL_ABSENCE = ClassRef(f"{prepend_model}Absence")
MODEL_LANGUAGE = ClassRef(f"{prepend_model}Language")
MODEL_OFFICE = ClassRef(f"{prepend_model}Office")
MODEL_ONBOARDING_PROGRESS = ClassRef(f"{prepend_model}OnboardingProgress")
MODEL_QUALIFICATION_USER = ClassRef(f"{prepend_model}QualificationUser")
MODEL_QUALIFICATION = ClassRef(f"{prepend_model}Qualification")
MODEL_RATE = ClassRef(f"{prepend_model}Rate")
MODEL_TENANT = ClassRef(f"{prepend_model}Tenant")
MODEL_USER = ClassRef(f"{prepend_model}User")
MODEL_PERMISSION = ClassRef("auth.Permission", django_native=True)
MODEL_CONTENT_TYPE = ClassRef("contenttypes.ContentType", django_native=True)
MODEL_GROUP = ClassRef("auth.Group", django_native=True)
MODEL_SCORE = ClassRef(f"{prepend_model}Score")
