from rest_framework.fields import empty
from rest_framework.serializers import BaseSerializer


def set_serializer_fields(fields, old_fields):
    allowed = set(fields)
    old = set(old_fields)
    for field in old.intersection(allowed):
        old_fields.pop(field)


class CustomSerializer(BaseSerializer):
    def __init__(self, instance=None, data=empty, **kwargs):
        fields = kwargs.pop('exclude', None)
        super().__init__(instance, data, **kwargs)
        if fields:
            set_serializer_fields(fields, self.fields)
