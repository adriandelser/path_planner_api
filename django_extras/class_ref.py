import inspect
import logging
from pydoc import locate

from django.apps import apps

logger = logging.getLogger(__name__)


class ClassRef:
    # todo: Refactor this class (name/certain sub functionality) to reflect current
    #  use for any lazy import
    def __init__(self, ref, django_native=False):
        """only one specified variable will take effect order is priority.
        ref=Reference to any class:
        e.g. accounts.models.user
        inst= any class
        e.g. ClassRef
        """
        self._django_native = django_native
        self.ref = ref
        self.ref_model = None
        # if it's a model then to get the reference in django remove .mdels
        # from path
        if ".models" in self.ref:
            self.ref_model = self.ref.replace(".models", "")
        # instance is retrieved lazily
        self._instance = None

    @property
    def ref(self):
        return self._ref

    @ref.setter
    def ref(self, model_path):
        self._ref = model_path

    @property
    def instance(self):
        """
        Returns instance of class e.g. ClassRef
        """
        if not self._instance:
            if self._django_native:
                obj = apps.get_model(self.ref)
            else:
                obj = locate(self.ref)
            if (
                not inspect.isclass(obj)
                and not inspect.isfunction(obj)
                and not inspect.ismodule(obj)
            ):
                raise Exception(
                    f"Ref error, object: {self._ref} is not a class or function"
                )
            self._instance = obj

        return self._instance

    def __hash__(self):
        return self.ref
