from typing import Set, Type

from django.db import models
from django.db.models import DateTimeField, JSONField

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


def JSONObjectValidator(value):
    if not isinstance(value, dict):
        raise ValidationError("Value must be a dict/JSON object")


class JSONMetaField(JSONField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("help_text", "Meta data for an entity")
        super().__init__(*args, **kwargs)
        self.validators.append(JSONObjectValidator)


class TimestampField(DateTimeField):
    def db_type(self, connection):
        return "timestamp"


class LTreeField(models.TextField):
    description = "ltree"

    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        kwargs["null"] = True
        kwargs["default"] = None
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        return "ltree"

    def to_python(self, value):
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ValueError(
                f"Ltree parent value: {value} of type {type(value)} must "
                f"be or type str or None"
            )
        return value


class AncestorsLookup(models.Lookup):
    lookup_name = "ancestors"

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return "%s @> %s" % (lhs, rhs), params


class DescendantsLookup(models.Lookup):
    lookup_name = "descendants"

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return "%s <@ %s" % (lhs, rhs), params


class ChildrenLookup(models.Lookup):
    lookup_name = "children"

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params + rhs_params
        return f"({lhs} <@ {rhs} AND nlevel({lhs}) = nlevel({rhs}) + 1)", params


# Register for ModelSerializer auto detection
serializers.ModelSerializer.serializer_field_mapping[
    JSONMetaField
] = serializers.JSONField
LTreeField.register_lookup(ChildrenLookup)
LTreeField.register_lookup(AncestorsLookup)
LTreeField.register_lookup(DescendantsLookup)


def default_choices_class():
    class DefaultChoices(models.TextChoices):
        OPTION_1 = "option1"
        OPTION_2 = "option2"

    return DefaultChoices


class SubsetLookup(models.Lookup):
    lookup_name = "subset"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return f"string_to_array({rhs}, ' ') <@ string_to_array({lhs}, ' ')", params


class HasLookup(models.Lookup):
    lookup_name = "has"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return f"{rhs} = ANY(string_to_array({lhs}, ' '))", params


class SetChoiceField(models.TextField):
    def __init__(self, *args, choices_class: Type[models.TextChoices] = None, **kwargs):
        self.choices_class = choices_class or default_choices_class()
        self._allowed_choices: Set[models.TextChoices] = set(self.choices_class)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        if isinstance(value, set):
            return value
        if value is None:
            return set()
        if not isinstance(value, str):
            raise ValueError(
                f"Set choice field value: {value} of type {type(value)} must "
                f"be or type str, space separated"
            )
        return set(self.choices_class(item) for item in value.split())

    def get_prep_value(self, value: Set[models.TextChoices]):
        if isinstance(value, models.TextChoices):
            return value.value
        elif isinstance(value, str):
            return value
        return " ".join(getattr(item, "value", item) for item in sorted(value))

    def validate(self, value: Set[models.TextChoices], model_instance):
        if not all(isinstance(item, self.choices_class) for item in value):
            raise ValueError(
                "All items in the set must be instances of the specified "
                "choices class"
            )
        if not value.issubset(self._allowed_choices):
            raise ValueError(
                f"All items in the set must be defined in the specified "
                f"choices class. Invalid items: "
                f"{value - self._allowed_choices}"
            )


SetChoiceField.register_lookup(SubsetLookup)
SetChoiceField.register_lookup(HasLookup)
