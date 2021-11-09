from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from mobileapi.serializers.organisation import UserOrganisationFavouriteSerializer
from organisation.models import UserOrganisationFavorites, Organisation


class UserOrganisationFavouriteViewSet(viewsets.ModelViewSet):
    serializer_class = UserOrganisationFavouriteSerializer
    permission_classes = (IsAuthenticated,)
    queryset = UserOrganisationFavorites.objects.none()

    def get_queryset(self):
        return UserOrganisationFavorites.objects.filter(user=self.request.user,
                                                        organisation__is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        if request.data.get('organisation'):
            if Organisation.objects.filter(id=request.data.get('organisation'), is_deleted=False).exists():
                if UserOrganisationFavorites.objects.filter(user=self.request.user,
                                                            organisation=request.data.get('organisation')).exists():
                    UserOrganisationFavorites.objects.filter(user=self.request.user,
                                                             organisation=request.data.get('organisation')).delete()
                    return Response({"message": "organisation remove from favourite"}, status=status.HTTP_200_OK)
                return super(UserOrganisationFavouriteViewSet, self).create(request, *args, **kwargs)
            return Response({"error": "organisation with this id doesn't exists"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({"missing_organisation": "organisation id is missing from json body"},
                        status=status.HTTP_404_NOT_FOUND)
