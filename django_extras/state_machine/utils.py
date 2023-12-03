from typing import Dict

import transitions
from transitions.core import Condition, EventData


class TransitionWithMeta(transitions.Transition):
    """
    Allows to specify some meta info about the transition in YAML
    such as if the transition should have an api trigger.

        transitions:
        -
            trigger: accept
            ...
            meta:
                api_trigger: yes
    """

    _meta: Dict

    def __init__(self, *args, **kwargs):
        self._meta = kwargs.pop("meta", dict())
        super(TransitionWithMeta, self).__init__(*args, **kwargs)
        self.conditions.append(Condition(func=self._check_perms))

    @property
    def meta(self):
        return self._meta

    @property
    def permissions(self):
        return self.meta.get("permissions", list())

    def _check_perms(self, evt: EventData):
        return evt.model.can_transition(self, *evt.args, **evt.kwargs)


class DynamicallyNamedMachine(transitions.Machine):
    """
    Helps to dynamically name state machines
    based of model names.
    """

    transition_cls = TransitionWithMeta
    _name: str

    def __init__(self, *args, id=None, name: str = None, model=None, **kwargs):
        if name is None:
            raise RuntimeError(
                "Expected DynamicallyNamedMachine to be initialized with name"
            )
        self._name = name
        if hasattr(model, "pk"):
            self._name = f"{self._name}<{model.pk}>"
        super().__init__(*args, model=model, **kwargs)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        pass
