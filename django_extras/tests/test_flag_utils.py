from django_extras.flag_utils import FeatureFlags


class TestFeatureFlags:
    def test_feature_flags_rate_change_snapshot_flag(self):
        # ARRANGE / ACT
        # ASSERT
        assert FeatureFlags.rate_change_snapshot_flag is True

    def test_feature_flags_empty(self, settings):
        # ARRANGE
        test_flags = {}
        settings.FEATURE_FLAGS = test_flags
        # ACT
        # ASSERT
        assert FeatureFlags.rate_change_snapshot_flag is False

    def test_feature_flags_false_value(
        self, s_ff_test_flag_pk, f_ff_test_flag_set_false
    ):
        # ARRANGE
        # ACT
        # ASSERT
        assert getattr(FeatureFlags, s_ff_test_flag_pk) is False

    def test_ff_filter_pk(self, s_ff_test_flag_pk, f_ff_test_flag_set_true):
        # ARRANGE
        # ACT
        ff = FeatureFlags.filter(pk=s_ff_test_flag_pk)
        # ASSERT
        assert ff == [
            {
                "name": s_ff_test_flag_pk,
                "state": FeatureFlags._get_flag(s_ff_test_flag_pk),
            }
        ]

    def test_ff_all(self, settings):
        # ARRANGE
        # ACT
        ff = FeatureFlags.all()
        # ASSERT
        assert ff == [
            {"name": k, "state": v} for k, v in settings.FEATURE_FLAGS.items()
        ]

    def test_ff_filter_no_pk_returns_all(self, mocker):
        # ARRANGE
        all_ = mocker.Mock()
        mocker.patch.object(FeatureFlags, "all", all_)
        # ACT
        FeatureFlags.filter()

        # ASSERT
        all_.assert_called_once()
