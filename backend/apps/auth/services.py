"""
Authentication business logic and services.
"""
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed
from shared.exceptions import ValidationException


class AuthService:
    """Service class for authentication operations."""
    
    @staticmethod
    def register_user(validated_data):
        """
        Register a new user.
        
        Args:
            validated_data: Dictionary containing user registration data
            
        Returns:
            User instance
        """
        from apps.auth.serializers import RegisterSerializer
        serializer = RegisterSerializer(data=validated_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return user
    
    @staticmethod
    def login_user(email, password):
        """
        Authenticate user and generate tokens.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            Dictionary containing access and refresh tokens
            
        Raises:
            AuthenticationFailed: If credentials are invalid
        """
        user = authenticate(username=email, password=password)
        
        if user is None:
            raise AuthenticationFailed('Invalid email or password')
        
        if not user.is_active:
            raise AuthenticationFailed('User account is disabled')
        
        refresh = RefreshToken.for_user(user)
        
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': user
        }
    
    @staticmethod
    def refresh_token(refresh_token):
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            New access token
        """
        try:
            refresh = RefreshToken(refresh_token)
            return {
                'access': str(refresh.access_token)
            }
        except Exception as e:
            raise AuthenticationFailed('Invalid refresh token')
