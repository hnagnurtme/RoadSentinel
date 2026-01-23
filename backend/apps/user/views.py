"""
User profile API endpoints.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema

from apps.user.models import UserProfile
from apps.user.serializers import UserProfileSerializer, UpdateProfileSerializer
from shared.responses.success import SuccessResponse
from shared.responses.error import ErrorResponse


class ProfileView(APIView):
    """User profile management endpoint."""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: UserProfileSerializer,
            404: 'Profile not found'
        }
    )
    def get(self, request):
        """Get current user's profile."""
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            serializer = UserProfileSerializer(profile)
            return SuccessResponse(
                data=serializer.data,
                message="Profile retrieved successfully"
            )
        except Exception as e:
            return ErrorResponse(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    @swagger_auto_schema(
        request_body=UpdateProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: 'Bad Request'
        }
    )
    def put(self, request):
        """Update current user's profile."""
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            serializer = UpdateProfileSerializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            response_serializer = UserProfileSerializer(profile)
            return SuccessResponse(
                data=response_serializer.data,
                message="Profile updated successfully"
            )
        except Exception as e:
            return ErrorResponse(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
