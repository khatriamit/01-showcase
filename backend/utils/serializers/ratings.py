from rest_framework import serializers

from booking.models import RatingReply
from users.serializers import BasicUserSerializer


class RatingReplyFilteredSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.filter(is_deleted=False)
        return super(RatingReplyFilteredSerializer, self).to_representation(data)


class RatingReplySerializer(serializers.ModelSerializer):
    """
    serializer for crud rating reply
    """
    reply_by = BasicUserSerializer(required=False, read_only=True)

    class Meta:
        # list_serializer_class = RatingReplyFilteredSerializer
        model = RatingReply
        fields = [
            "id",
            "reply_message",
            "reply_by",
            "reply_to"
        ]


class RatingReplyViewSetSerializer(serializers.ModelSerializer):
    """
    serializer for crud rating reply
    """
    reply_by = BasicUserSerializer(required=False, read_only=True)

    class Meta:
        model = RatingReply
        fields = [
            "id",
            "reply_message",
            "reply_by",
            "reply_to"
        ]