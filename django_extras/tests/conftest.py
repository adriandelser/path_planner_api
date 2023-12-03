import pytest

from ..serializers_utils import ParentSerializer


@pytest.fixture(scope="session")
def test_model_parent_serializer_class(test_model_class):
    class TestModelTreeSerializer(ParentSerializer):
        class Meta:
            model = test_model_class
            fields = ParentSerializer.Meta.fields + ("field1",)

    return TestModelTreeSerializer


@pytest.fixture(scope="session")
def test_model_serializer_class(test_model_class, test_model_parent_serializer_class):
    class TestModelSerializer(ParentSerializer):
        tree_serializer = test_model_parent_serializer_class

        class Meta(ParentSerializer.Meta):
            model = test_model_class
            fields = ParentSerializer.Meta.fields + (
                "field1",
                "field2",
                "protected_field",
                "choice_field",
            )

    return TestModelSerializer


@pytest.fixture(scope="session")
def seeded_graph_test_models(factory_seed_graph_data_for_model, test_model_class):
    root = factory_seed_graph_data_for_model(test_model_class)
    return root
