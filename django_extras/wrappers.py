import functools
import warnings

from django.db.models.signals import pre_save
from django.dispatch import receiver


def deprecated(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"{func.__name__} is deprecated and will be removed in a future version.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper


class ProtectFields:
    def __init__(self, sender, fields):
        self.sender = sender
        self.fields = set(fields)

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(instance, **kwargs):
            tracked_changes = dict(instance.tracker.changed())
            tracked_protected = self.fields.intersection(set(tracked_changes.keys()))
            for field in tracked_protected:
                if not getattr(instance, field):
                    setattr(instance, field, tracked_changes[field])

            return func(instance, **kwargs)

        # Register the wrapped function as a receiver for the specified signal and sender
        receiver(pre_save, sender=self.sender)(wrapper)
        return wrapper
