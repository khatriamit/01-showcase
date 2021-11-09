from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from mobileapi.serializers.organisation import OrganisationRoomSerializer
from organisation.models import Room


class OrganisationRoomView(generics.ListAPIView):
    """
    viewset for listing all the rooms of organisation
    """
    serializer_class = OrganisationRoomSerializer

    def get_queryset(self):
        organisation_id = self.request.query_params.get('organisation')
        rooms = Room.objects.all()
        if organisation_id:
            rooms = rooms.filter(organisation__id=organisation_id)
        return rooms


