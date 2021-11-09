from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from mobileapi.serializers.user import *

User = get_user_model()


class UserInfoView(RetrieveUpdateAPIView):
    """
    user profile info view
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = UserInfoSerializer

    def get_object(self):
        user = User.objects.get(id=self.request.user.id)
        return user

    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            self.get_object(), context={"request": self.request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
