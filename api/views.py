from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from .models import PlayerProfile, Team, Match
from .serializers import PlayerProfileSerializer, TeamSerializer, MatchSerializer, UserRegisterSerializer
from .permissions import RoleEnum, role_required
from .utils import api_response
from django.core.exceptions import ValidationError

import logging

logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    
class PlayerView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER, RoleEnum.CAPTAIN, RoleEnum.PLAYER)
    def get(self, request, player_id=None):
        try:
            if player_id:
                player = PlayerProfile.objects.get(id=player_id)
                serializer = PlayerProfileSerializer(player)
                return Response(api_response(data=serializer.data))
            
            players = PlayerProfile.objects.all().order_by('id')
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(players, request)
            serializer = PlayerProfileSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        except PlayerProfile.DoesNotExist:
            return Response(api_response(message="Player not found", code=404), status=404)
        except Exception as e:
            logger.exception("Error fetching player(s)")
            return Response(api_response(message="Server error", code=500), status=500)

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER, RoleEnum.CAPTAIN)
    def post(self, request):
        serializer = PlayerProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(api_response(data=serializer.data, message="Player created", code=201), status=201)
        return Response(api_response(data=serializer.errors, message="Validation failed", code=400), status=400)

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER, RoleEnum.CAPTAIN, RoleEnum.PLAYER)
    def put(self, request, player_id):
        try:
            player = PlayerProfile.objects.get(id=player_id)
            if request.user.category == RoleEnum.PLAYER and player.user != request.user:
                return Response(api_response(message="Unauthorized", code=403), status=403)
            serializer = PlayerProfileSerializer(player, data=request.data, partial=True)
            if serializer.is_valid():
                try:
                    serializer.save()
                except ValidationError as ve:
                    return Response(api_response(data=ve.message_dict, message="Validation failed", code=400), status=400)
                return Response(api_response(data=serializer.data, message="Player updated"))
            return Response(api_response(data=serializer.errors, message="Validation failed", code=400), status=400)
        except PlayerProfile.DoesNotExist:
            return Response(api_response(message="Player not found", code=404), status=404)
        except Exception:
            logger.exception("Unexpected error while updating player")
            return Response(api_response(message="Server error", code=500), status=500)

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER, RoleEnum.CAPTAIN)
    def delete(self, request, player_id):
        try:
            player = PlayerProfile.objects.get(id=player_id)
            if player.user != request.user and request.user.category != RoleEnum.ADMIN:
                return Response(api_response(message="Unauthorized", code=403), status=403)
            player.delete()
            return Response(api_response(message="Player deleted"))
        except PlayerProfile.DoesNotExist:
            return Response(api_response(message="Player not found", code=404), status=404)
        except Exception:
            logger.exception("Error deleting player")
            return Response(api_response(message="Server error", code=500), status=500)

class TeamView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER, RoleEnum.CAPTAIN)
    def get(self, request, team_id=None):
        try:
            if team_id:
                team = Team.objects.get(id=team_id)
                serializer = TeamSerializer(team)
                return Response(api_response(data=serializer.data))
            teams = Team.objects.all().order_by('id')  # Add ordering
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(teams, request)
            serializer = TeamSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)  # Simplified response
        except Team.DoesNotExist:
            return Response(api_response(message="Team not found", code=404), status=404)
        except Exception:
            logger.exception("Error fetching team(s)")
            return Response(api_response(message="Server error", code=500), status=500)
        
    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER)
    def post(self, request):
        serializer = TeamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(api_response(data=serializer.data, message="Team created", code=201), status=201)
        return Response(api_response(data=serializer.errors, message="Validation failed", code=400), status=400)

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER)
    def put(self, request, team_id):
        try:
            team = Team.objects.get(id=team_id)
            serializer = TeamSerializer(team, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(api_response(data=serializer.data, message="Team updated"))
            return Response(api_response(data=serializer.errors, message="Validation failed", code=400), status=400)
        except Team.DoesNotExist:
            return Response(api_response(message="Team not found", code=404), status=404)
        except Exception:
            logger.exception("Error updating team")
            return Response(api_response(message="Server error", code=500), status=500)

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER)
    def delete(self, request, team_id):
        try:
            team = Team.objects.get(id=team_id)
            team.delete()
            return Response(api_response(message="Team deleted"))
        except Team.DoesNotExist:
            return Response(api_response(message="Team not found", code=404), status=404)
        except Exception:
            logger.exception("Error deleting team")
            return Response(api_response(message="Server error", code=500), status=500)

class MatchView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER)
    def get(self, request, match_id=None):
        try:
            if match_id:
                match = Match.objects.get(id=match_id)
                serializer = MatchSerializer(match)
                return Response(api_response(data=serializer.data))
            matches = Match.objects.all().order_by('id')
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(matches, request)
            serializer = MatchSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Match.DoesNotExist:
            return Response(api_response(message="Match not found", code=404), status=404)
        except Exception:
            logger.exception("Error fetching match(es)")
            return Response(api_response(message="Server error", code=500), status=500)

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER)
    def post(self, request):
        serializer = MatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(api_response(data=serializer.data, message="Match created", code=201), status=201)
        return Response(api_response(data=serializer.errors, message="Validation failed", code=400), status=400)

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER)
    def put(self, request, match_id):
        try:
            match = Match.objects.get(id=match_id)
            serializer = MatchSerializer(match, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(api_response(data=serializer.data, message="Match updated"))
            return Response(api_response(data=serializer.errors, message="Validation failed", code=400), status=400)
        except Match.DoesNotExist:
            return Response(api_response(message="Match not found", code=404), status=404)
        except Exception:
            logger.exception("Error updating match")
            return Response(api_response(message="Server error", code=500), status=500)

    @role_required(RoleEnum.ADMIN, RoleEnum.ORGANISER)
    def delete(self, request, match_id):
        try:
            match = Match.objects.get(id=match_id)
            match.delete()
            return Response(api_response(message="Match deleted"))
        except Match.DoesNotExist:
            return Response(api_response(message="Match not found", code=404), status=404)
        except Exception:
            logger.exception("Error deleting match")
            return Response(api_response(message="Server error", code=500), status=500)
class RegisterUserView(APIView):
    def post(self, request):
        try:
            serializer = UserRegisterSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(api_response(data=serializer.data, message="User registered", code=201), status=201)
            return Response(api_response(data=serializer.errors, message="Validation failed", code=400), status=400)
        except Exception:
            logger.exception("Error registering user")
            return Response(api_response(message="Server error", code=500), status=500)
