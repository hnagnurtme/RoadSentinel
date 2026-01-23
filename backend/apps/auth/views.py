"""
Authentication API endpoints.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.auth.serializers import RegisterSerializer, LoginSerializer, UserSerializer
from apps.auth.services import AuthService
from shared.responses.success import SuccessResponse
from shared.responses.error import ErrorResponse


class RegisterView(APIView):
    """User registration endpoint."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response('User registered successfully', UserSerializer),
            400: 'Bad Request'
        }
    )
    def post(self, request):
        """Register a new user."""
        try:
            user = AuthService.register_user(request.data)
            serializer = UserSerializer(user)
            return SuccessResponse(
                data=serializer.data,
                message="User registered successfully",
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return ErrorResponse(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class LoginView(APIView):
    """User login endpoint."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={
            200: 'Login successful',
            401: 'Unauthorized'
        }
    )
    def post(self, request):
        """Authenticate user and return tokens."""
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            result = AuthService.login_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password']
            )
            
            user_serializer = UserSerializer(result['user'])
            
            return SuccessResponse(
                data={
                    'user': user_serializer.data,
                    'tokens': {
                        'access': result['access'],
                        'refresh': result['refresh']
                    }
                },
                message="Login successful"
            )
        except Exception as e:
            return ErrorResponse(
                message=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED
            )


class RefreshTokenView(APIView):
    """Refresh access token endpoint."""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            200: 'Token refreshed',
            401: 'Unauthorized'
        }
    )
    def post(self, request):
        """Generate new access token from refresh token."""
        try:
            refresh_token = request.data.get('refresh')
            result = AuthService.refresh_token(refresh_token)
            return SuccessResponse(
                data=result,
                message="Token refreshed successfully"
            )
        except Exception as e:
            return ErrorResponse(
                message=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
