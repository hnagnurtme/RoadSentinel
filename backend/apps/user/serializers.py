"""
User profile serializers.
"""
from rest_framework import serializers
from apps.user.models import UserProfile
from apps.auth.serializers import UserSerializer


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'bio', 'avatar', 'date_of_birth', 'address', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""
    class Meta:
        model = UserProfile
        fields = ['bio', 'avatar', 'date_of_birth', 'address']
