from rest_framework import status
from rest_framework.response import Response


class FollowerRequestMixin:

    @staticmethod
    def generate_response(response):
        data = {'status': response}
        if response in ['Accepted', 'Rejected']:
            return Response(data, status.HTTP_200_OK)
        else:
            return Response(data, status.HTTP_400_BAD_REQUEST)
