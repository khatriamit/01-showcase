from django.contrib.auth import get_user_model
from rest_framework import serializers
from booking.models import RatingByIndividual
from utils.serializers import ratings


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    serializer for the user short info
    """
    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'profile_picture'
        ]


class FilteredListSerializer(serializers.ListSerializer):

    def to_representation(self, data):
        data = data.filter(is_deleted=False)
        return super(FilteredListSerializer, self).to_representation(data)


class RatingByIndividualSerializer(serializers.ModelSerializer):
    """
    serializer for the rating and review of organisation
    """
    rated_by = UserSerializer(read_only=True)
    rating_reply = ratings.RatingReplySerializer(read_only=True, many=True)

    class Meta:
        list_serializer_class = FilteredListSerializer
        model = RatingByIndividual
        fields = [
            'id',
            'rated_on',
            'comments',
            'rating_star',
            'rated_by',
            'location',
            'comfort',
            'personnel',
            'cleanliness',
            'good_offer',
            'service',
            'created_on',
            'modified_on',
            'deleted_on',
            'is_deleted',
            'rating_reply'
        ]