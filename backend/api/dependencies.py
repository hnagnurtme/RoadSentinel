# from typing import Annotated
#
# import jwt
# from fastapi import Depends, HTTPException, status
# from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.orm import selectinload
#
#
# async def get_current_user(
#         credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
#         db: Annotated[AsyncSession, Depends(get_db)],
# ) -> User:
#     """Get the current authenticated user from JWT token."""
#     jwt_service = _get_jwt_service()
#
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#
#     if credentials is None:
#         raise credentials_exception
#
#     try:
#         payload = jwt_service.decode_token(credentials.credentials)
#         user_id_str = payload.get("sub")
#         token_type: str | None = payload.get("type")
#
#         if user_id_str is None or token_type != "access":
#             raise credentials_exception
#
#         # Convert user_id to int (JWT stores as string per standard)
#         user_id = int(user_id_str)
#
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token has expired",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     except jwt.InvalidTokenError:
#         raise credentials_exception
#
#     # Get user from database with organization eagerly loaded
#     result = await db.execute(
#         select(User)
#         .where(User.id == user_id)
#         .options(selectinload(User.organization))
#     )
#     user = result.scalar_one_or_none()
#
#     if user is None:
#         raise credentials_exception
#
#     if not user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="User account is deactivated",
#         )
#
#     return user
#
#
# # Type alias for current user dependency
# CurrentUser = Annotated[User, Depends(get_current_user)]