import pytest
from model_bakery import baker


@pytest.mark.django_db
def test_protect_fields(test_model_class):
    # Modify both fields
    initial_value = "initial"
    test_model = baker.make(
        test_model_class,
        field1=initial_value,
        field2=initial_value,
        protected_field=initial_value,
    )
    test_model.update(
        field1="",
        field2="new value",
        protected_field="",
    )

    # Refresh the instance from the database
    test_model.refresh_from_db()

    # Check if the protected field (field1) is not changed
    assert test_model.protected_field == initial_value

    # Check if the unprotected field (field2) is changed
    assert test_model.field1 == ""
    assert test_model.field2 == "new value"
