import math

import pytest
from model_bakery import baker

from ..fields import SetChoiceField
from ..models_utils import ParentModel


class TestUpdateableMixin:
    @pytest.mark.parametrize(
        ["fields", "raises"],
        [
            ({"field1": "another_value", "field2": "20"}, False),
            ({"field1": "new_value"}, False),
            ({}, False),
            ({"pk": "10", "field1": "new_value"}, True),
            ({"non_existent_field": "some_value"}, True),
            ({"bypass_orm": True, "field1": "another_value", "field2": "20"}, False),
            ({"bypass_orm": True, "field1": "new_value"}, False),
            (
                {
                    "bypass_orm": True,
                },
                False,
            ),
            ({"bypass_orm": True, "pk": "10", "field1": "new_value"}, True),
            ({"bypass_orm": True, "non_existent_field": "some_value"}, True),
        ],
    )
    def test_updatable_mixin_update(
        self, db, fields: dict, raises: bool, test_model_class
    ):
        instance = baker.make(test_model_class, field1="old_value", field2="10")
        if raises:
            # Test updating with an invalid field name (raises AttributeError)
            with pytest.raises(Exception):
                instance.update(**fields)
            return
        instance.update(**fields)
        instance.refresh_from_db()
        for key, val in fields.items():
            if hasattr(instance, key):
                assert getattr(instance, key) == val


class TestParentSerializer:
    @pytest.mark.parametrize(["max_depth"], [(None,), (0,), (1,), (2,), (3,), (4,)])
    def test_tree_bfs(
        self,
        db,
        max_depth,
        test_model_serializer_class,
        seeded_graph_test_models,
        test_model_parent_serializer_class,
        mock_request,
    ):
        # ARRANGE
        root = seeded_graph_test_models
        data = {"max_depth": max_depth}
        if max_depth is None:
            data = {}
            max_depth = math.inf
        mock_request.query_params = data
        serializer = test_model_serializer_class(
            root, context={"request": mock_request}
        )
        # ACT
        result = serializer.get_tree(root)

        # ASSERT
        if max_depth > 3:
            assert len(result) == 10
        # ASSERT that the result contains the expected number of nodes (1 root + 3*3
        # tree = 10)
        # ASSERT that the root node is at depth 0
        assert result[str(seeded_graph_test_models.id)]["depth"] == 0
        assert set(result[str(seeded_graph_test_models.id)].keys()) == set(
            test_model_parent_serializer_class.Meta.fields
        ).difference({"max_depth"}).union({"children", "depth"})
        # ASSERT that the children's depths are correctly calculated
        for node_id, node_data in result.items():
            if node_id != str(seeded_graph_test_models.id):
                assert 1 <= node_data["depth"] <= max_depth

    def test_tree_bfs_all_children_exist(
        self, db, test_model_serializer_class, seeded_graph_test_models, mock_request
    ):
        # ARRANGE
        root = seeded_graph_test_models
        data = {"max_depth": 0}
        mock_request.query_params = data
        serializer = test_model_serializer_class(
            root, context={"request": mock_request}
        )  # ACT
        result = serializer.get_tree(root)

        # ASSERT
        assert len(result) == 1
        result = result[str(root.id)]
        assert len(result.get("children")) == 0, result.get("children")
        assert result.get("depth") == 0, result.get("depth")

    def test_tree_bfs_no_children_have_self(
        self, db, test_model_serializer_class, seeded_graph_test_models, mock_request
    ):
        # ARRANGE
        root = seeded_graph_test_models
        serializer = test_model_serializer_class(root)
        # ACT
        result = serializer.get_tree(root)

        # ASSERT
        for node_id, node_data in result.items():
            assert node_data.get("id") not in node_data.get("children")

    def test_bfs_graph_correct(
        self, db, test_model_serializer_class, seeded_graph_test_models, mock_request
    ):
        # ARRANGE
        root = seeded_graph_test_models
        depth_node_count = {0: 1, 1: 3, 2: 3, 3: 3}
        serializer = test_model_serializer_class(root)
        # ACT
        result = serializer.get_tree(root)

        # ASSERT
        for node_id, node_data in result.items():
            assert node_data.get("id") not in node_data.get("children")
            depth_node_count[node_data.get("depth")] -= 1
        assert list(depth_node_count.values()) == [0, 0, 0, 0]

    def test_ancestral_tree_graph_correct(
        self, db, test_model_serializer_class, seeded_graph_test_models, mock_request
    ):
        # ARRANGE
        root: ParentModel = seeded_graph_test_models
        child = root.children.all()[0].children.all()[0].children.all()[0]
        depth_node_count = {0: 1, 1: 3, 2: 3, 3: 3}
        serializer = test_model_serializer_class(root)
        # ACT
        result = serializer.get_ancestral_tree(child)

        # ASSERT
        for node_id, node_data in result.items():
            assert node_data.get("id") not in node_data.get("children")
            depth_node_count[node_data.get("depth")] -= 1
        assert list(depth_node_count.values()) == [0, 0, 0, 0]

    @pytest.mark.parametrize(["max_depth"], [(-1,), (None,), ("a",)])
    def test_serializer_raises_ignores_invalid_max_depth(
        self,
        db,
        max_depth,
        test_model_serializer_class,
        seeded_graph_test_models,
        mock_request,
    ):
        # ARRANGE
        root = seeded_graph_test_models
        data = {"max_depth": max_depth}
        mock_request.query_params = data
        serializer = test_model_serializer_class(
            root, context={"request": mock_request}
        )
        # ACT
        result = serializer.get_tree(root)
        # ASSERT
        assert len(result) == 10

    def test_serializer_optimization(
        self,
        db,
        test_model_serializer_class,
        seeded_graph_test_models,
        db_threshold_factory,
    ):
        # ARRANGE
        root = seeded_graph_test_models
        serializer = test_model_serializer_class(root)
        # ACT
        # TODO: children prefetch somehow to avoid n+1 if possible.
        with db_threshold_factory("localhost", 10, 12):
            result = serializer.get_tree(root)
        # ASSERT
        assert len(result) == 10


class TestSetChoiceField:
    def test_from_db_value(self, test_model_choices_class):
        field = SetChoiceField(test_model_choices_class)
        db_value = " ".join(["option1", "option2"])
        python_value = field.from_db_value(db_value, None, None)
        assert isinstance(python_value, set)
        assert python_value == {
            test_model_choices_class.OPTION_1,
            test_model_choices_class.OPTION_2,
        }

    def test_to_python(self, test_model_choices_class):
        field = SetChoiceField(test_model_choices_class)
        db_value = " ".join(["option1", "option2"])
        python_value = field.to_python(db_value)
        assert isinstance(python_value, set)
        assert python_value == {
            test_model_choices_class.OPTION_1,
            test_model_choices_class.OPTION_2,
        }

    def test_get_prep_value(self, test_model_choices_class):
        field = SetChoiceField(test_model_choices_class)
        python_value = {
            test_model_choices_class.OPTION_1,
            test_model_choices_class.OPTION_2,
        }
        db_value = field.get_prep_value(python_value)
        assert isinstance(db_value, str)
        assert db_value == " ".join(["option1", "option2"])

    def test_validate(self, test_model_choices_class):
        field = SetChoiceField(test_model_choices_class)
        with pytest.raises(
            ValueError,
            match="All items in the set must be instances of "
            "the specified choices class",
        ):
            field.validate({"invalid_choice"}, None)

    def test_field_value(self, db, test_model_class, test_model_choices_class):
        instance = test_model_class(choice_field={test_model_choices_class.OPTION_1})
        instance.save()
        assert instance.choice_field == {test_model_choices_class.OPTION_1}

    def test_field_set_operations(self, db, test_model_class, test_model_choices_class):
        instance = test_model_class(choice_field={test_model_choices_class.OPTION_1})
        instance.clean()
        instance.save()
        instance.refresh_from_db()

        instance.choice_field.add(test_model_choices_class.OPTION_2)
        instance.clean()
        instance.save()
        instance.refresh_from_db()
        assert instance.choice_field == {
            test_model_choices_class.OPTION_1,
            test_model_choices_class.OPTION_2,
        }

        instance.choice_field.remove(test_model_choices_class.OPTION_1)
        instance.clean()
        instance.save()
        instance.refresh_from_db()
        assert instance.choice_field == {test_model_choices_class.OPTION_2}

        instance.choice_field.clear()
        instance.clean()
        instance.save()
        instance.refresh_from_db()
        assert instance.choice_field == set()

    def test_subset_filter(self, db, test_model_class, test_model_choices_class):
        m123 = test_model_class(
            choice_field={
                test_model_choices_class.OPTION_1,
                test_model_choices_class.OPTION_2,
                test_model_choices_class.OPTION_3,
            }
        )
        m123.save()
        m12 = test_model_class(
            choice_field={
                test_model_choices_class.OPTION_1,
                test_model_choices_class.OPTION_2,
            }
        )
        m12.save()
        m23 = test_model_class(
            choice_field={
                test_model_choices_class.OPTION_2,
                test_model_choices_class.OPTION_3,
            }
        )
        m23.save()
        m13 = test_model_class(
            choice_field={
                test_model_choices_class.OPTION_1,
                test_model_choices_class.OPTION_3,
            }
        )
        m13.save()
        result = test_model_class.objects.filter(
            choice_field__subset={
                test_model_choices_class.OPTION_1,
                test_model_choices_class.OPTION_2,
            }
        )
        assert len(result) == 2 and m12 in result and m123 in result

    def test_order_independence(self, db, test_model_class, test_model_choices_class):
        m12 = test_model_class(
            choice_field={
                test_model_choices_class.OPTION_1,
                test_model_choices_class.OPTION_2,
            }
        )
        m12.save()
        result = test_model_class.objects.filter(
            choice_field__subset={
                test_model_choices_class.OPTION_2,
                test_model_choices_class.OPTION_1,
            }
        )
        assert len(result) == 1 and m12 in result

    def test_has_filter(self, db, test_model_class, test_model_choices_class):
        m1 = test_model_class(choice_field={test_model_choices_class.OPTION_1})
        m1.save()
        m12 = test_model_class(
            choice_field={
                test_model_choices_class.OPTION_1,
                test_model_choices_class.OPTION_2,
            }
        )
        m12.save()
        m2 = test_model_class(
            choice_field={
                test_model_choices_class.OPTION_2,
            }
        )
        m2.save()

        # Testing single option
        result = test_model_class.objects.filter(
            choice_field__has=test_model_choices_class.OPTION_1
        )
        assert len(result) == 2 and m1 in result and m12 in result

        # Testing option not in any set

        result = test_model_class.objects.filter(
            choice_field__has=test_model_choices_class.OPTION_3
        )
        assert len(result) == 0
