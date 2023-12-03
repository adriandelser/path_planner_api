import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Feature flags, False by default."""

    def __init__(self):
        self._validate_flags()

    def _validate_flags(self):
        for key, val in settings.FEATURE_FLAGS.items():
            if not hasattr(self, key):
                raise RuntimeError(
                    f"Feature Flag:{key} is not defined in FeatureFlags cls"
                )

    @property
    def _test_flag(self):
        return self._get_flag("_test_flag")

    @property
    def rate_change_snapshot_flag(self) -> bool:
        return self._get_flag("rate_change_snapshot_flag")

    @property
    def enable_task_alerts_flag(self) -> bool:
        return self._get_flag("enable_task_alerts_flag")

    @property
    def cp_4164_croudie_statuses(self) -> bool:
        return self._get_flag("cp_4164_croudie_statuses")

    @property
    def cp_4828_onboarding_progress_flag(self) -> bool:
        return self._get_flag("cp_4828_onboarding_progress_flag")

    def _get_flag(self, flag_name):
        return settings.FEATURE_FLAGS.get(flag_name, False)

    def all(self):
        return [{"name": k, "state": v} for k, v in settings.FEATURE_FLAGS.items()]

    def filter(self, pk=None):
        if pk:
            state = settings.FEATURE_FLAGS.get(pk)
            if state is None:
                return []
            return [{"name": pk, "state": state}]
        return self.all()


FeatureFlags = FeatureFlags()
