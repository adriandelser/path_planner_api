from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache

CACHE_KEY_CONTENT_TYPE = "content_type"


class CacheMiddleware:
    # django_extras.cache.ContentTypeCacheMiddleware
    def __init__(self, get_response):
        self.get_response = get_response
        cache_content_types()

    def __call__(self, request):
        return self.get_response(request)


def cache_content_types():
    for ct in ContentType.objects.all():
        cache.set(f"{CACHE_KEY_CONTENT_TYPE}{ct.app_label}:{ct.model}", ct)


def get_content_type_for_model(model):
    app_label = model._meta.app_label
    model_name = model._meta.model_name
    ct = cache.get(f"content_type:{app_label}:{model_name}")
    if ct is None:
        ct = ContentType.objects.get(app_label=app_label, model=model_name)
        cache.set(f"content_type:{app_label}:{model_name}", ct)
    return ct


def get_model_by_name(model_name):
    model = cache.get(model_name)

    if model is None:
        for model in apps.get_models():
            if model.__name__.lower() == model_name.lower():
                cache.set(model_name, model)
                return model

        raise ValueError(f"No model found for '{model_name}'")

    return model
