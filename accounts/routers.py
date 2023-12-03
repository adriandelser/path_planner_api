from rest_framework.routers import SimpleRouter
from rest_framework_nested import routers


class NestedAndRootPathRouter(routers.NestedMixin, SimpleRouter):
    """
    Provides list/create routes with nested paths and detail routes
    with direct paths so detail views can be accessed without
    specifying a `parent_id` url kwarg.

    e.g. List/Create paths: `users/{user_pk}/absences/{id}`
         Detail paths: `absences/{id}`

    """

    def __init__(self, *args, **kwargs):
        detail_routes = []
        non_detail_routes = []

        # Filter out detail routes
        for route in self.routes:
            if route.detail:
                detail_routes.append(route)
            else:
                non_detail_routes.append(route)

        self.routes = non_detail_routes

        # Allow `rest_framework_nested` to process nested routes
        super().__init__(*args, **kwargs)

        # Re-set both direct and nested routes
        self.routes = detail_routes + self.routes
