from typing import List

from django.db.models import Model, Q, QuerySet


def combine_querysets_on_field(querysets: List[QuerySet], field: str, model: Model):
    """
    Combine multiple QuerySets based on a common field.

    Parameters:
    querysets (List): A list of QuerySets to combine.
    field (str): The common field on which to combine.
    model: The model of the resulting QuerySet.

    Returns:
    A QuerySet of the model specified.
    """

    q_objects = Q()  # Create an empty Q object

    for queryset in querysets:
        q_objects |= Q(**{f"{field}__in": queryset.values(field)})

    combined_queryset = model.objects.filter(
        q_objects
    )  # Filter the model objects using the Q object

    return combined_queryset
