from django.urls import path
from .views import PlayerView, TeamView, MatchView, RegisterUserView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='user-register'),
    
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('players/', PlayerView.as_view()),
    path('players/<int:player_id>/', PlayerView.as_view()),
    
    path('teams/', TeamView.as_view()),
    path('teams/<int:team_id>/', TeamView.as_view()),
    
    path('matches/', MatchView.as_view()),
    path('matches/<int:match_id>/', MatchView.as_view()),
    
    
]
