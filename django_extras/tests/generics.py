from typing import Dict

from model_bakery import baker


def model_fields_protected(model_cls, fields: Dict):
    instance = baker.make(model_cls, **fields)
    for field in fields.keys():
        assert (
            field in model_cls.tracker.fields
        ), f"Field {field} not tracked by {model_cls} hence will not be protected"
        assert (
            getattr(instance, field) is not None
        ), f"Field {field} of {instance} should not be None"
        try:
            setattr(instance, field, None)
            instance.save()
            is_field_none = getattr(instance, field) is None
            assert (
                not is_field_none
            ), f"{field} should be protected from being set to None"
        except ValueError:
            # If a ValueError is raised, the field is protected from being set to None
            pass
