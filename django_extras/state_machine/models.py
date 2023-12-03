from __future__ import annotations

import json
import os
from copy import deepcopy
from enum import Enum
from functools import cached_property
from pydoc import locate
from typing import Callable, Dict, List, Set, Type, Union

from django.conf import settings
from django.db import models
from django.db.models import Model, Q
from django.dispatch import Signal

from transitions import EventData, MachineError

from core.utils.generic import get_request_user_from_id
from django_extras.celery import default_shared_task
from django_extras.config.models_foreign import MODEL_USER
from django_extras.state_machine.utils import (
    DynamicallyNamedMachine,
    TransitionWithMeta,
)


class Transitions(Enum):
    # store transitions and transitions_api for fast lookup
    # transitions is the set of state machine function names attached
    _transitions: Set
    # transition_api is the mapping of function name url repr to function names (in
    # _transitions)
    _transitions_api: Dict[str:str]

    @classmethod
    def _depreciated(cls):
        return False

    @classmethod
    def _transitions_private(cls) -> Set:
        return set()

    @classmethod
    def transitions(cls) -> Set[str]:
        if not hasattr(cls, "_transitions"):
            cls._transitions = {v.value for v in cls}
        return cls._transitions

    @classmethod
    def get_model(cls) -> Type[Model]:
        raise NotImplementedError

    @classmethod
    def get_transition_permissions(cls, transitions: Set[str]) -> Set[str]:
        return {
            f"transition_{cls.get_model().__name__.lower()}_{transition}"
            for transition in transitions
        }

    @classmethod
    def transitions_api(
        cls, user=None, as_sorted_list=False, as_str: str = None
    ) -> Union[Dict[str, str], List, str]:
        """
        Parameters
        ----------
        as_sorted_list returns sorted list of api formatted transition names
        as_str return sorted str with specified delimter e.g. ', '.join(sorted(...))
        """

        """
           Parameters
           ----------
           as_sorted_list: bool
               returns sorted list of api formatted transition names
           delimiter: str
               return sorted str with specified delimiter e.g. ', '.join(sorted(...))
           """

        if not hasattr(cls, "_transitions_api"):
            format_value = lambda v: v.value.replace("_", "-")  # noqa
            if cls._depreciated():
                format_value = lambda v: v.value  # noqa

            cls._transitions_api = {
                format_value(v): v.value
                for v in cls
                if v.value not in cls._transitions_private()
            }

        if as_sorted_list or as_str is not None:
            transitions = sorted(
                cls.transitions() - cls._transitions_private()
                if cls._depreciated()
                else cls._transitions_api.keys()
            )
            if as_str is not None:
                return as_str.join(transitions)
            return transitions
        return (
            cls._transitions_api if user is None else None
        )  # please replace with actual user handling logic


class StateMachineDefinition:
    """Takes care of loading a state machine based from its directory given an entity"""

    _transitions_set: Set[str]

    def __init__(self, entity, path=None):
        self._path_definition = path
        if path is None:
            self._path_definition = self.get_state_machine_path(entity)
        with open(f"{path}/definition.json", "r") as f:
            self.definition = json.load(f)
        self._path_module = self.to_module_path(self._path_definition)
        self.background_actions_module = locate(
            f"{self._path_module}.background_actions"
        )
        self.synchronous_actions_module = locate(
            f"{self._path_module}.synchronous_actions"
        )

    @property
    def transitions_set(self) -> Set[str]:
        if not hasattr(self, "_transitions_set"):
            self._transitions_set = {
                t.get("trigger") for t in self.definition.get("transitions")
            }
        return self._transitions_set

    @staticmethod
    def to_module_path(state_machine_path):
        """
        state_machine_path = {root_dir}/{app_label}/state_machine/{state_machine_name}
        module_path = {app_label}.state_machine.{state_machine_name}
        Parameters
        ----------
        state_machine_path

        Returns
        -------
        """
        return ".".join(state_machine_path.split("/")[-3:])

    @staticmethod
    def get_state_machine_path(entity, default=False):
        base_path = (
            f"{settings.ROOT_DIR}/{entity.__class__._meta.app_label}/state_machine/"
            f"{entity.__class__._meta.verbose_name.lower()}_"
        )
        if default:
            return f"{base_path}default"
        machine_type = getattr(entity, "type", "default")
        if hasattr(entity, "type_id"):
            machine_type = entity.type_id
        path = f"{base_path}{machine_type}"
        # avoid isfile check
        if path in entity._machine_definition:
            return path
        if not os.path.isdir(path):
            path = f"{base_path}default"
            # avoid isfile check
            if path in entity._machine_definition:
                return path
            if not os.path.isdir(path):
                raise MachineError(f"Path does not exist: {path}")
        return path

    def __hash__(self):
        return self.path

    def __eq__(self, other):
        return self.path == other.path


#
# @dataclasses.dataclass
# class EventSignalKwargs:
#     sender: StateMachineModel.__class__  # event_data.model.__class__,
#     instance: StateMachineModel
#     entity_id: str
#     source: EventData.transition
#     target: transition.dest,
#     transition: transition_dict,
#     transition_name: event_data.event.name,
#     request_user_id: event_data.kwargs.pop("user_id", None),
#     data: event_data.kwargs.get("payload") or {},
#     kwargs: event_data.kwargs or {},
#
#


class StateMachineModel(models.Model):
    """
    An abstract base class model that provides
    state machine properties.
    """

    post_transition = Signal()
    _transitions_cls: Transitions
    _machine: DynamicallyNamedMachine
    _machine_definition: Dict[str, StateMachineDefinition]
    _synchronous_actions_fn: Callable
    _state_machine_methods: Set = {"trigger", "machine"}
    _creating: bool = False
    _transition_user = None

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bypass_perms: bool = False
        # init state machine

    def __getattr__(self, name):
        # all possible machine methods to determine initialization (can't get local methods as not initialized)
        if name in self._state_machine_methods | self.transitions_cls.transitions():
            if self._creating:
                raise AttributeError()
            if not hasattr(self, "_machine"):
                self.create_machine()
            # local state machine methods to ensure attr actually exists
            if (
                name
                in self.machine_definition().transitions_set
                | self._state_machine_methods
            ):
                return getattr(self, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}', is in machine "
            f"methods: {name in self._state_machine_methods}"
        )

    def transition(
        self, transition_name: str, bypass_perms=False, save=False, **kwargs
    ):
        self._bypass_perms = bypass_perms
        result = self.trigger(transition_name, **kwargs)
        self._bypass_perms = False
        if save:
            self.save()
        return result

    @classmethod
    @property
    def transitions_cls(cls) -> Transitions:
        if not hasattr(cls, "_transitions_cls"):
            try:
                app_label = cls.__module__.split(".")[0]
                transition_path = (
                    f"{app_label}.state_machine.utils.{cls.__name__}Transitions"
                )
                cls._transitions_cls: Transitions = locate(transition_path)
            except ImportError:
                raise RuntimeError(
                    f"Could not find {transition_path} class for {app_label} "
                    f"instantiating {cls.__name__}"
                )
        return cls._transitions_cls

    @property
    def machine(self) -> DynamicallyNamedMachine:
        if not hasattr(self, "_machine"):
            self.create_machine()
        return self._machine

    @cached_property
    def available_transitions(self, *args, **kwargs) -> Dict:
        """
        Get available transitions for the entity.
        """
        transitions = dict()
        event_data = EventData(
            state=self.state,
            event=None,
            machine=self.machine,
            model=self,
            args=args,
            kwargs=kwargs,
        )
        for trigger in self.machine.get_triggers(self.state):
            event = self.machine.events[trigger]

            event_transitions: List[
                List[TransitionWithMeta]
            ] = event.transitions.values()
            transitions[trigger] = all(
                any(
                    condition.check(event_data)
                    # TransitionWithMeta.conditions
                    for condition in transition[0].conditions
                )
                for transition in event_transitions
            )
        transitions = {
            trigger: dict()
            for trigger, can_transition in transitions.items()
            if can_transition
        }
        return transitions

    def create_machine(
        self,
        *,
        send_event=True,
        auto_transitions=False,
        **extra_kwargs,
    ):
        """
        Create a `transitions.Machine` based on yaml definition.

        Arguments:
            name: Name of the machine definition
            model: Django model instance
            initial: initial state
            **extra_kwargs: Passed on the `transitions.Machine` initialisation
        """
        if self._creating:
            raise RuntimeError("Machine is being created")
        # this is to ensure that the machine isn't being created multiple times at
        # any point.
        self._creating = True
        common_args = {
            "prepare_event": self.prepare_event,
            "send_event": send_event,
            "auto_transitions": auto_transitions,
            "initial": self.state,
            "model": self,
            "after_state_change": self.entity_transitioned,
        }
        definition = self.machine_definition().definition
        assert set(extra_kwargs).isdisjoint(
            set(definition) | set(common_args)
        ), "Arguments override definition"

        self._machine = DynamicallyNamedMachine(
            **definition, **common_args, **extra_kwargs
        )
        self._creating = False

    def can_transition(
        self, transition: TransitionWithMeta, *args, user_id=None, **kwargs
    ) -> bool:
        """Check if user can call transition given meta permissions
        -> This is executed on `available_transitions` via the `_has_perm` in TransitionWithMeta.


        Parameters
        ----------
        user:
        transition

        Returns
        -------
        bool: True if user has any of the required permissions or no permissions are
        necessary (empty list)
        """
        if not settings.AUTHZ_ACTIVE or self._bypass_perms:
            return True

        result = False
        # not pretty, but we have less restraint on non-user objects
        # we only care if the result is set to False for these.
        if not isinstance(self, MODEL_USER.instance):
            result = True
        # _transition_user may have been assigned if a user_id (from a request) does not exist.
        # this might need to be reworked at some point. we use it as cache to avoid retrieving the user
        # every time.
        if self._transition_user is None and user_id is not None:
            self._transition_user = MODEL_USER.instance.objects.get(id=user_id)
        if self._transition_user is None:
            return True

        # PERMISSION LAYER
        # groups to check if transition.permissions exist in
        relevant_groups = None
        # The new system only operates over the User model, we can use the new system
        # over all state machines by removing this conditional.
        if isinstance(self, MODEL_USER.instance):
            # global_permission is a `special` permission related to the state machine
            # which if a group contains it, the other permissions in that group
            # operate over all users inheriting the state machine, rather than just self.
            global_permission = (
                f"state_machine_{self.__class__.__name__.lower()}_{self.type}"
            )
            # aggregate relevant groups depending if we are operating over self or another user
            # if we want to expand this to other state machines, the conditional for whether or not an
            # object relates to a user will have to be more complex than just `pk` comparison.
            if self._transition_user.pk != self.pk:
                relevant_groups = self._transition_user.groups.filter(
                    Q(permissions__codename=global_permission)
                )
            else:
                relevant_groups = self._transition_user.groups.filter(
                    ~Q(permissions__codename__icontains="state_machine_")
                )
        else:
            # OLD STANDARD to be depreciated.
            if transition.permissions:
                return any(
                    self._transition_user.has_perm(f"users.{permission}")
                    for permission in transition.permissions
                )
            return True
        if relevant_groups is not None:
            # we only operate over groups for now, user assigned permissions are ignored.
            result = relevant_groups.filter(
                permissions__codename__in=transition.permissions
            ).exists()
        return result

    @classmethod
    def prepare_event(cls, event_data):
        """
        Sets a `last_transition` property on a
        transitioned entity if the property exists.
        """

        if not hasattr(event_data.model, "last_transition"):
            return

        # Drop trailing _ which is used by convention on
        # transition names that overlap with protected names
        event_data.model.last_transition = event_data.event.name.rstrip("_")

    def machine_definition(self) -> StateMachineDefinition:
        cls = self.__class__
        if not hasattr(cls, "_machine_definition"):
            cls._machine_definition = dict()
        path = StateMachineDefinition.get_state_machine_path(self)
        if path not in cls._machine_definition:
            cls._machine_definition[path] = StateMachineDefinition(
                entity=self, path=path
            )
        return cls._machine_definition[path]

    @staticmethod
    @default_shared_task()
    def perform_background_action(**kwargs):
        sender = locate(kwargs.get("sender"))
        request_user = get_request_user_from_id(kwargs.get("request_user_id"))
        entity: StateMachineModel = sender.objects.get(pk=kwargs.get("entity_id"))
        kwargs["entity"] = entity
        kwargs["request_user"] = request_user
        action = getattr(
            entity.machine_definition().background_actions_module,
            kwargs.get("transition_name"),
            None,
        )
        entity._perform_background_action_pre(action=action, **kwargs)
        if action:
            action(entity, **kwargs)
        entity._perform_background_action_post(action=action, **kwargs)
        entity.save()

    def perform_synchronous_action(self, **kwargs):
        kwargs["request_user"] = get_request_user_from_id(kwargs.get("request_user_id"))
        action = getattr(
            self.machine_definition().synchronous_actions_module,
            kwargs.get("transition_name"),
            None,
        )
        self._perform_synchronous_action_pre(action=action, **kwargs)
        if action:
            action(self, **kwargs)
        self._perform_synchronous_action_post(action=action, **kwargs)
        self.save()

    def _perform_background_action_pre(self, action: Callable = None, **kwargs):
        ...

    def _perform_background_action_post(self, action: Callable = None, **kwargs):
        ...

    def _perform_synchronous_action_pre(self, action: Callable = None, **kwargs):
        ...

    def _perform_synchronous_action_post(self, action: Callable = None, **kwargs):
        ...

    @classmethod
    def get_entity_transitioned_signal_kwargs(cls, event_data, transition):
        transition_dict = deepcopy(event_data.transition.__dict__)
        transition_dict.pop("conditions", None)
        # TODO: remove all this, unnecessary complexity, replace with dataclass for legibility
        return {
            "sender": event_data.model.__class__,
            "instance": event_data.model,
            "entity_id": str(event_data.model.id),
            "source": transition.source,
            "target": transition.dest,
            "transition": transition_dict,
            "transition_name": event_data.event.name,
            "request_user_id": event_data.kwargs.pop("user_id", None),
            "data": event_data.kwargs.get("payload") or {},
            "kwargs": event_data.kwargs or {},
        }

    @classmethod
    def entity_transitioned(cls, event_data: EventData):
        """
        Fires a signal which can be hooked into
        after a successful transition.
        """
        transition = event_data.transition
        signal_kwargs = cls.get_entity_transitioned_signal_kwargs(
            event_data, transition
        )
        event_data.model.perform_synchronous_action(**signal_kwargs)
        cls.post_transition.send(**signal_kwargs)
