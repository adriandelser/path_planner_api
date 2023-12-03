import collections
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from django.db.models import Prefetch, QuerySet

import six
from drf_partial_response.views import OptimizedQuerySetBase, OptimizedQuerySetMixin


@dataclass
class Mutation:
    _mutations: Optional[List[Callable[[QuerySet], QuerySet]]] = None

    priority: int = 0
    base_queryset: QuerySet = None

    @property
    def mutations(self) -> List[Callable[[QuerySet], QuerySet]]:
        if self._mutations is None:
            self._mutations = list()
        return self._mutations

    def add(
        self,
        mutation: Callable[[QuerySet], QuerySet],
        base_queryset: QuerySet,
        priority: int = 0,
    ):
        if priority > self.priority or self.base_queryset is None:
            self.base_queryset = base_queryset
        self.mutations.append(mutation)

    def apply_all(self) -> QuerySet:
        queryset = self.base_queryset
        for mutation in self.mutations:
            queryset = mutation(queryset)
        return queryset


class PrefetchKwargs:
    def __init__(self, lookup: str, to_attr=None):
        self.lookup = lookup
        self.to_attr = to_attr

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __hash__(self):
        return hash(f"{self.lookup}_{self.to_attr}")


@six.add_metaclass(OptimizedQuerySetBase)
class OptimizedQuerySetAnnotationsMixin(OptimizedQuerySetMixin):
    """Extends OptimizedQuerySetMixin to allow for combining annotations rather than
    prefetching at each data predicate instantiation.
    by using add_nested_queryset_mutation, all mutations will be stored and applied once
    optimization is called at the end.

    """

    _mutations: Dict[PrefetchKwargs, Mutation] = None

    @property
    def mutations(self) -> Dict[PrefetchKwargs, Mutation]:
        if self._mutations is None:
            self._mutations = collections.defaultdict(Mutation)
        return self._mutations

    def _clean(self):
        self._mutations = None

    def get_queryset(self):
        self._clean()
        queryset = super(OptimizedQuerySetMixin, self).get_queryset()
        queryset = self.optimize_queryset(queryset)
        queryset = self.apply_all_data_functions(queryset)
        return queryset

    def add_nested_queryset_mutation(
        self,
        lookup: str,
        base_queryset: QuerySet,
        queryset_transformer_lambda: Callable[[QuerySet], QuerySet] = None,
        base_queryset_priority: int = 0,
        to_attr: str = None,
    ):
        """

        Parameters
        ----------
        lookup
        base_queryset
        queryset_transformer_lambda
        base_queryset_priority
        to_attr
        Returns
        -------

        """
        if queryset_transformer_lambda is None:
            queryset_transformer_lambda = lambda q: q.all()  # noqa
        self.mutations[PrefetchKwargs(lookup=lookup, to_attr=to_attr)].add(
            queryset_transformer_lambda, base_queryset, base_queryset_priority
        )

    def apply_all_data_functions(self, queryset):
        for prefetch_kwargs, mutation in self.mutations.items():
            queryset = queryset.prefetch_related(
                Prefetch(
                    lookup=prefetch_kwargs.lookup,
                    queryset=mutation.apply_all(),
                    to_attr=prefetch_kwargs.to_attr,
                )
            )
        return queryset
