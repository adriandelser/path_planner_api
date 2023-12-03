import math
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from rest_framework import serializers

from .models_utils import ParentModel


class ParentSerializer(serializers.ModelSerializer):
    tree = serializers.SerializerMethodField()
    ancestral_tree = serializers.SerializerMethodField()
    _max_depth: int = math.inf
    _cached_queryset: Optional[Dict[Any, ParentModel]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_queryset: Optional[Dict[Any, ParentModel]] = dict()

    class Meta:
        model = ParentModel
        fields = ("id", "parent")

    @property
    def max_depth(self):
        # TODO: how are we managing query params for get requests...
        if "request" in self.context:
            max_depth = self.context.get("request").query_params.get("max_depth", None)
            try:
                max_depth = int(max_depth)
                if max_depth > -1:
                    self._max_depth = max_depth
            except (ValueError, TypeError):
                pass
        return self._max_depth

    @property
    def cached_queryset(self):
        return self._cached_queryset

    @cached_queryset.setter
    def cached_queryset(
        self, val: Tuple[ParentModel, Callable[[ParentModel], Set[int]]]
    ):
        root, get_descendants = val
        # if the root exists, we can assume all of it's descendants are there
        # no need to delete cache.
        if root in self._cached_queryset:
            return
        # we have new id's to cache
        ids = get_descendants(root)
        queryset = (
            root.__class__.objects.filter(id__in=ids)
            .exclude(id=None)
            .select_related("parent")
        )
        self._cached_queryset.update({obj.id: obj for obj in queryset})

    def bfs_traversal(
        self,
        root: ParentModel,
        get_children_func: Callable[[ParentModel], Set[int]],
        get_descendants_func: Callable[[ParentModel], Set[int]],
        assign_children_func: Callable[[Dict[str, Any], Set[int]], None],
    ) -> dict[str, dict[str, Any]]:
        """
         Perform a breadth-first search (BFS) traversal starting from a root instance.

        Parametersget_descendants_func
        ----------
        root: The root instance to start the traversal from.
        get_children_func: A function that takes an instance and returns a list of
                            IDs of its children.
        assign_children_func: A function that takes a representation dictionary and a
                              list of child IDs,
                              and assigns the child IDs to the representation
                              dictionary.

        Returns
        -------

        """
        queue: List[Tuple[ParentModel, int]] = [
            (root, 0)
        ]  # Start with the root object. Tuple: (instance, depth)
        cache: Dict[
            str, Dict[str, Any]
        ] = {}  # Cache for storing the serialized data of instances
        tree_serializer = getattr(self, "tree_serializer", None)
        self.cached_queryset = root, get_descendants_func
        while queue:
            current_instance, depth = queue.pop(0)

            if str(current_instance.id) in cache:
                continue

            # which serializer should we use
            if not tree_serializer:
                representation = super().to_representation(current_instance)
            else:
                representation = tree_serializer(current_instance).data
            # mark the depth & cache
            representation["depth"] = depth
            cache[str(current_instance.id)] = representation

            children_ids = set()
            # as we are performing bfs, we can cut off computation at depth-1
            if depth < self.max_depth:
                # Use the provided function to get the children' IDs
                children_ids = get_children_func(current_instance)

                for child_id in children_ids:
                    if child_id not in self.cached_queryset:
                        # If the child is not found there is an issue
                        # with the get_descendants function from the root
                        # raise an error.
                        error_info = {
                            "root_node": root.id,
                            "descendant_function": str(get_descendants_func),
                            "retrieved_descendants": str(get_descendants_func(root)),
                            "bfs_child_not_found": child_id,
                            "parent_node": current_instance.id,
                            "retrieved_children": str(children_ids),
                            "cached_queryset_keys": str(self.cached_queryset.keys()),
                        }

                        raise RuntimeError(error_info)
                    queue.append((self.cached_queryset.get(child_id), depth + 1))

            # Use the provided function to assign the children to the representation
            assign_children_func(representation, children_ids)
        return cache  # Return the cache containing serialized data of all processed

    def get_ancestral_tree(self, obj: ParentModel) -> dict[str, dict[str, Any]]:
        """Get the tree of the parent without parents (root)
        Returns
        -------

        """
        while obj.parent_id:
            obj = obj.parent
        return self.get_tree(obj)

    def get_tree(self, obj: ParentModel) -> dict[str, dict[str, Any]]:
        """
        Get the serialized data of a model instance and it's tree at max_depth.

        Parameters:
        obj: The instance to get the serialized data of.

        Returns:
        A dictionary where each key is an instance ID, and the value is the
        serialized data for that instance.
        """

        # Perform BFS traversal and return the resulting dictionary
        return self.bfs_traversal(
            root=obj,
            get_children_func=lambda x: set(x.children.values_list("id", flat=True)),
            get_descendants_func=lambda x: set(
                x.descendants.values_list("id", flat=True)
            ),
            assign_children_func=lambda rep, child_ids: rep.update(
                {"children": child_ids}
            ),
        )
