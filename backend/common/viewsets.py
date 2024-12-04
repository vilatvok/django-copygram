from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet, ModelViewSet


class NonUpdateViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    pass


class ListModelViewSet(mixins.ListModelMixin, GenericViewSet):
    pass


class CustomModelViewSet(ModelViewSet):
    @staticmethod
    def generate_action_response(response):
        pass

    def get_action_response(self, request, func):
        from_user = request.user
        to_user = self.get_object()
        response = func(from_user, to_user)
        return self.generate_action_response(response)
