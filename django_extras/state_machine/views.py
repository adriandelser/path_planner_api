from django.db import transaction

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from transitions import MachineError

from core.state_machine.transition_serializers import validate_transition_payload
from core.utils.permissions import ModelActionPermission
from django_extras.state_machine.models import StateMachineModel
from users.config.models_foreign import MODEL_TASK


class StateMachineViewMixin:
    def get_object(self):
        obj = super().get_object()
        obj._transition_user = self.request.user
        return obj

    @classmethod
    def generate_transition_method(
        cls,
        queryset,
        transitions_url_path: str = "transition",
        transition_permission_classes=None,
        transition_detail=True,
        bypass_acl_check=False,
    ):
        if transition_permission_classes is None:
            transition_permission_classes = [ModelActionPermission]
        # Retrieve necessary parameters from class

        @extend_schema(
            operation_id=f"{queryset.model.__name__.lower()}s_transition",
            description=f"Transition a {queryset.model.__name__.lower()}: `{queryset.model.transitions_cls.transitions_api(as_str=', ')}`",
            parameters=[
                OpenApiParameter(
                    "name",
                    OpenApiTypes.STR,
                    OpenApiParameter.PATH,
                    enum=queryset.model.transitions_cls.transitions_api(
                        as_sorted_list=True
                    ),
                ),
            ],
            examples=[
                OpenApiExample(
                    name=f"Transition Payload: {transition}",
                    value="{}",
                    description=f"This transition will set a {queryset.model.__name__.lower()} as `{transition}`",
                )
                for transition in queryset.model.transitions_cls.transitions_api(
                    as_sorted_list=True
                )
            ],
            responses={
                status.HTTP_200_OK: None,
                status.HTTP_403_FORBIDDEN: None,
                status.HTTP_409_CONFLICT: None,
            },
        )
        @action(
            methods=["post"],
            detail=transition_detail,
            url_path=f"{transitions_url_path}/(?P<name>{queryset.model.transitions_cls.transitions_api(as_str='|')})",
            permission_classes=transition_permission_classes,
        )
        def transition(self, request, name: str, *args, **kwargs):
            """
            Provides a method for transitioning entities
            within a view returning an api response.
            """
            name = queryset.model.transitions_cls.transitions_api()[name]
            obj: StateMachineModel = self.get_object()

            payload = validate_transition_payload(obj, name, request.data)

            try:
                with transaction.atomic():
                    trigger_success = obj.trigger(
                        name,
                        payload=payload,
                        user_id=request.user.id,
                    )
                    if not trigger_success:
                        raise PermissionDenied(detail=f"Transition {name} not allowed")
                    obj.save()

            except MachineError as e:
                return Response(
                    {
                        "transition": name,
                        "conflict": e.args[0],
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Populate fresh nested data after a successful transition
            get_object_params = (
                {"bypass_acl_check": bypass_acl_check} if bypass_acl_check else {}
            )
            instance = self.get_object(**get_object_params)
            serializer_kwargs = {"instance": instance, "return_nested_data": True}

            if type(instance) != MODEL_TASK.instance:
                serializer_kwargs.update({"context": {"request": request}})

            response_serializer = self.get_serializer(**serializer_kwargs)

            return Response(data=response_serializer.data, status=status.HTTP_200_OK)

        return transition
