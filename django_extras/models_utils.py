from functools import cached_property

from django.contrib.postgres import indexes
from django.db import DEFAULT_DB_ALIAS, models
from django.db.models.signals import pre_save

from . import fields


class UpdatableMixin(models.Model):
    class Meta:
        abstract = True

    def update(
        self,
        bypass_orm=False,
        commit=True,
        **fields,
    ) -> None:
        """Update fields of a model's instance, triggering signals
        Parameters
        ----------
        bypass_orm: exec update as SQL_UPDATE bypassing ORM features such as signals
        fields

        Returns
        -------

        """
        if bypass_orm:
            self.__class__.objects.filter(pk=self.pk).update(**fields)
            return
        modified_fields = []

        for field, new_value in fields.items():
            current_value = getattr(self, field)

            if current_value != new_value:
                setattr(self, field, new_value)
                if commit:
                    modified_fields.append(field)

        if modified_fields:
            self.save(update_fields=modified_fields)

    def save(self, *args, commit=True, **kwargs):
        # Call the save method of the parent class (or mixins) to ensure all logic is executed
        if not commit:
            pre_save.send(
                sender=type(self),
                instance=self,
                raw=False,
                using=kwargs.get("using", DEFAULT_DB_ALIAS),
                update_fields=kwargs.get("update_fields"),
            )
            return
        super().save(*args, **kwargs)


class ParentModel(models.Model):
    """
    An abstract base class model that provides
    a `parent` field.
    The model implements the LTreeField with
    `path`, which is using the `id`.

    """

    path = fields.LTreeField(help_text="Path used for the ltree on %(class)")

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        db_index=False,
        on_delete=models.CASCADE,
        help_text="The parent %(class)",
        related_name="%(class)s_parent",
    )

    class Meta:
        indexes = [
            indexes.BTreeIndex(fields=["path"]),
            indexes.GistIndex(fields=["path"]),  # For querying ancestors / descendants.
        ]
        abstract = True

    @cached_property
    def ancestors(self):
        model = type(self)
        return model.objects.filter(path__ancestors=self.path)

    @cached_property
    def descendants(self):
        model = type(self)
        return model.objects.filter(path__descendants=self.path)

    @cached_property
    def children(self):
        model = type(self)
        return model.objects.filter(path__children=self.path)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # for triggers refresh from db.
        self.refresh_from_db()
