from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry
from taggit.models import Tag


@registry.register_document
class TagDocument(Document):
    class Index:
        name = 'tags'
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    class Django:
        model = Tag
        fields = ['name']
