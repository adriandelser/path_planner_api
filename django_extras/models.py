# Django extras should have no models, only ones for testing
# we only uncomment here to create a migration
# that should be moved to test_migrations as 0001_initial.py
# when we want to add a new field for testing.
# make sure to reflect changes in generics.test_model_class under tests.

# from django.db import models
# from model_utils import FieldTracker
#
# from django_extras.models_utils import ParentModel, SetChoiceField


# class TestModel(ParentModel, UpdatableMixin, models.Model):
#     class Choices(models.TextChoices):
#         OPTION_1 = "option1"
#         OPTION_2 = "option2"
#         OPTION_3 = "option3"
#     field1 = models.CharField(max_length=100, default="", blank=True)
#     field2 = models.CharField(max_length=100, default="", blank=True)
#     protected_field = models.CharField(max_length=100, default="", null=True)
#     tracker = FieldTracker()
#     choice_field = SetChoiceField(
#         choices_class=Choices, default=set, null=True
#     )
