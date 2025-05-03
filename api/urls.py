from django.urls import path
from .views import PlayerView, TeamView, MatchView, RegisterUserView
from rest_framework_simplejwt.views import (TokenObtainPairView,TokenRefreshView,)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(title="Cricket API", default_version='v1'),
    public=True,
)

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='user-register'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('players/', PlayerView.as_view(), name='player-list'),
    path('players/<int:player_id>/', PlayerView.as_view(), name='player-detail'),
    path('teams/', TeamView.as_view(), name='team-list'),
    path('teams/<int:team_id>/', TeamView.as_view(), name='team-detail'),
    path('matches/', MatchView.as_view(), name='match-list'),
    path('matches/<int:match_id>/', MatchView.as_view(), name='match-detail'),
    
    path('swagger/', schema_view.with_ui('swagger'), name='schema-swagger-ui'),
]