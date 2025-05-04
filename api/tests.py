from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from api.models import CustomUser, Team, PlayerProfile, Match
from api.serializers import CustomUserSerializer, TeamSerializer, PlayerProfileSerializer, MatchSerializer, UserRegisterSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

CustomUser = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            username='admin', password='admin123', email='admin@example.com', category='ADMIN'
        )
        self.player_user = CustomUser.objects.create_user(
            username='player', password='player123', email='player@example.com', category='PLAYER'
        )
        self.organiser_user = CustomUser.objects.create_user(
            username='organiser', password='organiser123', email='organiser@example.com', category='ORGANISER'
        )
        self.captain_user = CustomUser.objects.create_user(
            username='captain', password='captain123', email='captain@example.com', category='CAPTAIN'
        )
        self.team = Team.objects.create(name='Team A', country='India', captain=self.captain_user)
        self.team2 = Team.objects.create(name='Team B', country='Australia')
        self.player_profile = PlayerProfile.objects.create(
            user=self.player_user, age=25, type='BATTER', team=self.team, is_playing=True
        )
        self.match = Match.objects.create(
            date=date.today(), venue='Stadium', team1=self.team, team2=self.team2
        )

    def test_custom_user_creation(self):
        """Test CustomUser model creation with valid category."""
        user = CustomUser.objects.create_user(
            username='testuser', password='test123', email='test@example.com', category='ORGANISER'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.category, 'ORGANISER')
        self.assertTrue(user.check_password('test123'))

    def test_custom_user_superuser_creation(self):
        """Test CustomUser superuser creation."""
        user = CustomUser.objects.create_superuser(
            username='superuser', password='super123', email='superuser@example.com'
        )
        self.assertEqual(user.username, 'superuser')
        self.assertTrue(user.check_password('super123'))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_custom_user_invalid_email(self):
        """Test CustomUser creation with missing email."""
        user = CustomUser.objects.create_user(
            username='noemail', password='test123', email='', category='PLAYER'
        )
        self.assertEqual(user.email, '')

    def test_custom_user_invalid_category(self):
        """Test CustomUser creation with invalid category."""
        user = CustomUser.objects.create_user(
            username='invalid', password='test123', email='invalid@example.com', category='INVALID'
        )
        self.assertEqual(user.category, 'INVALID')

    def test_custom_user_str(self):
        """Test CustomUser __str__ method."""
        self.assertEqual(str(self.admin_user), 'admin (ADMIN)')

    def test_team_points_calculation(self):
        """Test Team model's update_points method."""
        self.team.wins = 2
        self.team.draw = 1
        self.team.save()
        self.assertEqual(self.team.points, 5)  # (2 * 2) + 1 = 5

    def test_team_str(self):
        """Test Team model's __str__ method."""
        self.assertEqual(str(self.team), 'Team A')

    def test_team_nullable_captain(self):
        """Test Team with nullable captain."""
        team = Team.objects.create(name='Team C', country='England')
        self.assertIsNone(team.captain)
        self.assertEqual(team.points, 0)

    def test_player_profile_playing_eleven_validation(self):
        """Test PlayerProfile's clean method for playing XI limit (max 11 players)."""
        self.player_profile.is_playing = False
        self.player_profile.save()

        for i in range(11):
            user = CustomUser.objects.create_user(
                username=f'player{i}', password='pass123', email=f'player{i}@example.com', category='PLAYER'
            )
            PlayerProfile.objects.create(
                user=user, age=25, type='BATTER', team=self.team, is_playing=True
            )

        new_user = CustomUser.objects.create_user(
            username='extra', password='pass123', email='extra@example.com', category='PLAYER'
        )
        extra_player = PlayerProfile(
            user=new_user, age=25, type='BATTER', team=self.team, is_playing=True
        )
        with self.assertRaises(ValidationError):
            extra_player.full_clean()

    def test_player_profile_str(self):
        """Test PlayerProfile's __str__ method."""
        self.assertEqual(str(self.player_profile), 'player (BATTER)')

    def test_player_profile_team_required(self):
        """Test PlayerProfile requires a team."""
        new_user = CustomUser.objects.create_user(
            username='newplayer', password='pass123', email='newplayer@example.com', category='PLAYER'
        )
        with self.assertRaises(ValidationError):
            PlayerProfile.objects.create(
                user=new_user, age=25, type='BATTER', team=None, is_playing=False
            )

    def test_match_save_logic_new(self):
        """Test Match model's save method for new match updates."""
        self.match.winner = self.team
        self.match.save()
        self.team.refresh_from_db()
        self.team2.refresh_from_db()
        self.player_profile.refresh_from_db()
        self.assertEqual(self.team.wins, 1)
        self.assertEqual(self.team.matches_played, 1)
        self.assertEqual(self.team2.lost, 1)
        self.assertEqual(self.team2.matches_played, 1)
        self.assertEqual(self.player_profile.matches_played, 1)

    def test_match_save_logic_draw(self):
        """Test Match model's save method for draw."""
        self.team.draw = 0
        self.team2.draw = 0
        self.team.save()
        self.team2.save()
        self.match.save()  # No winner
        self.team.refresh_from_db()
        self.team2.refresh_from_db()
        self.assertEqual(self.team.draw, 1)
        self.assertEqual(self.team2.draw, 1)
        self.assertEqual(self.team.matches_played, 1)
        self.assertEqual(self.team2.matches_played, 1)

    def test_match_update_reverts_previous_stats(self):
        """Test Match model's save method reverts previous stats on update."""
        self.team.wins = 0
        self.team2.lost = 0
        self.team.save()
        self.team2.save()
        self.match.winner = self.team
        self.match.save()

        self.team.refresh_from_db()
        self.team2.refresh_from_db()
        self.assertEqual(self.team.wins, 1)
        self.assertEqual(self.team2.lost, 1)

        self.match.winner = None
        self.match.save()

        self.team.refresh_from_db()
        self.team2.refresh_from_db()
        self.assertEqual(self.team.wins, 0)
        self.assertEqual(self.team.draw, 1)
        self.assertEqual(self.team2.lost, 0)
        self.assertEqual(self.team2.draw, 1)

    def test_match_str(self):
        """Test Match model's __str__ method."""
        self.assertEqual(str(self.match), 'Team A vs Team B at Stadium')


class SerializerTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser', password='test123', email='test@example.com', category='PLAYER'
        )
        self.captain = CustomUser.objects.create_user(
            username='captain', password='cap123', email='captain@example.com', category='CAPTAIN'
        )
        self.team = Team.objects.create(name='Team A', country='India', captain=self.captain)

    def test_custom_user_serializer(self):
        """Test CustomUserSerializer serialization."""
        serializer = CustomUserSerializer(self.user)
        expected_data = {
            'id': self.user.id,
            'username': 'testuser',
            'email': 'test@example.com',
            'category': 'PLAYER'
        }
        self.assertEqual(serializer.data, expected_data)

    def test_team_serializer(self):
        """Test TeamSerializer serialization with players and captain."""
        PlayerProfile.objects.create(user=self.user, age=25, type='BATTER', team=self.team)
        serializer = TeamSerializer(self.team)
        expected_data = {
            'id': self.team.id,
            'name': 'Team A',
            'country': 'India',
            'matches_played': 0,
            'wins': 0,
            'lost': 0,
            'draw': 0,
            'points': 0,
            'created_at': serializer.data['created_at'],
            'players': [self.team.players.first().id],
            'captain': self.captain.id
        }
        self.assertEqual(serializer.data, expected_data)

    def test_team_serializer_no_players(self):
        """Test TeamSerializer with no players."""
        serializer = TeamSerializer(self.team)
        expected_data = {
            'id': self.team.id,
            'name': 'Team A',
            'country': 'India',
            'matches_played': 0,
            'wins': 0,
            'lost': 0,
            'draw': 0,
            'points': 0,
            'created_at': serializer.data['created_at'],
            'players': [],
            'captain': self.captain.id
        }
        self.assertEqual(serializer.data, expected_data)

    def test_player_profile_serializer_validation(self):
        """Test PlayerProfileSerializer validation and creation."""
        new_user = CustomUser.objects.create_user(
            username='newplayer', password='new123', email='newplayer@example.com', category='PLAYER'
        )
        data = {
            'user_id': new_user.id,
            'age': 30,
            'type': 'BOWLER',
            'team': self.team.id,
            'matches_played': 5,
            'total_runs': 100,
            'wickets': 10,
            'is_playing': False
        }
        serializer = PlayerProfileSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        player = serializer.save()
        self.assertEqual(player.age, 30)
        self.assertEqual(player.type, 'BOWLER')

    def test_player_profile_serializer_invalid_type(self):
        """Test PlayerProfileSerializer with invalid type."""
        data = {
            'user_id': self.user.id,
            'age': 30,
            'type': 'INVALID',
            'team': self.team.id,
            'is_playing': False
        }
        serializer = PlayerProfileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('type', serializer.errors)

    def test_player_profile_serializer_invalid_user_category(self):
        """Test PlayerProfileSerializer with non-PLAYER user."""
        data = {
            'user_id': self.captain.id,
            'age': 30,
            'type': 'BOWLER',
            'team': self.team.id,
            'is_playing': False
        }
        serializer = PlayerProfileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('user_id', serializer.errors)

    def test_match_serializer(self):
        """Test MatchSerializer serialization."""
        match = Match.objects.create(
            date=date.today(), venue='Stadium', team1=self.team, team2=Team.objects.create(name='Team B', country='Australia')
        )
        serializer = MatchSerializer(match)
        expected_dataGAS = {
            'id': match.id,
            'date': str(date.today()),
            'venue': 'Stadium',
            'team1': self.team.id,
            'team2': match.team2.id,
            'winner': None
        }
        self.assertEqual(serializer.data, expected_data)

    def test_match_serializer_same_teams(self):
        """Test MatchSerializer allows same team1 and team2."""
        data = {
            'date': str(date.today()),
            'venue': 'Stadium',
            'team1': self.team.id,
            'team2': self.team.id
        }
        serializer = MatchSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_match_serializer_invalid_date(self):
        """Test MatchSerializer with invalid date."""
        data = {
            'date': 'invalid-date',
            'venue': 'Stadium',
            'team1': self.team.id,
            'team2': Team.objects.create(name='Team B', country='Australia').id
        }
        serializer = MatchSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('date', serializer.errors)

    def test_user_register_serializer_valid(self):
        """Test UserRegisterSerializer for valid user creation."""
        data = {
            'username': 'newuser',
            'password': 'Test1234!',
            'password2': 'Test1234!',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'PLAYER'
        }
        serializer = UserRegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.username, 'newuser')
        self.assertTrue(user.check_password('Test1234!'))
        self.assertEqual(user.category, 'PLAYER')

    def test_user_register_serializer_password_mismatch(self):
        """Test UserRegisterSerializer for password mismatch."""
        data = {
            'username': 'newuser',
            'password': 'Test1234!',
            'password2': 'Different1234!',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'PLAYER'
        }
        serializer = UserRegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_user_register_serializer_invalid_email(self):
        """Test UserRegisterSerializer with invalid email."""
        data = {
            'username': 'newuser',
            'password': 'Test1234!',
            'password2': 'Test1234!',
            'email': 'invalid-email',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'PLAYER'
        }
        serializer = UserRegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_user_register_serializer_invalid_category(self):
        """Test UserRegisterSerializer with invalid category."""
        data = {
            'username': 'newuser',
            'password': 'Test1234!',
            'password2': 'Test1234!',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'INVALID'
        }
        serializer = UserRegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('category', serializer.errors)

    def test_user_register_serializer_weak_password(self):
        """Test UserRegisterSerializer with weak password."""
        data = {
            'username': 'newuser',
            'password': '123',
            'password2': '123',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'PLAYER'
        }
        serializer = UserRegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)


class APITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = CustomUser.objects.create_user(
            username='admin', password='admin123', email='admin@example.com', category='ADMIN'
        )
        self.organiser_user = CustomUser.objects.create_user(
            username='organiser', password='organiser123', email='organiser@example.com', category='ORGANISER'
        )
        self.captain_user = CustomUser.objects.create_user(
            username='captain', password='captain123', email='captain@example.com', category='CAPTAIN'
        )
        self.player_user = CustomUser.objects.create_user(
            username='player', password='player123', email='player@example.com', category='PLAYER'
        )
        self.team = Team.objects.create(name='Team A', country='India', captain=self.captain_user)
        self.team2 = Team.objects.create(name='Team B', country='Australia')
        self.player_profile = PlayerProfile.objects.create(
            user=self.player_user, age=25, type='BATTER', team=self.team
        )
        self.match = Match.objects.create(
            date=date.today(), venue='Stadium', team1=self.team, team2=self.team2
        )

        # Generate JWT tokens
        self.admin_token = RefreshToken.for_user(self.admin_user).access_token
        self.organiser_token = RefreshToken.for_user(self.organiser_user).access_token
        self.captain_token = RefreshToken.for_user(self.captain_user).access_token
        self.player_token = RefreshToken.for_user(self.player_user).access_token

    def authenticate(self, token):
        """Helper to set JWT token for authenticated requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    # PlayerView Tests
    def test_player_view_get_all_paginated(self):
        """Test GET /players/ with pagination for admin."""
        self.authenticate(self.admin_token)
        response = self.client.get(reverse('player-list'), {'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['user']['username'], 'player')

    def test_player_view_get_all_empty(self):
        """Test GET /players/ with no players."""
        PlayerProfile.objects.all().delete()
        self.authenticate(self.admin_token)
        response = self.client.get(reverse('player-list'), {'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 0)

    def test_player_view_get_single(self):
        """Test GET /players/<player_id>/ for admin."""
        self.authenticate(self.admin_token)
        response = self.client.get(reverse('player-detail', kwargs={'player_id': self.player_profile.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user']['username'], 'player')
        self.assertEqual(response.data['code'], '200')

    def test_player_view_get_single_captain(self):
        """Test GET /players/<player_id>/ for captain."""
        self.authenticate(self.captain_token)
        response = self.client.get(reverse('player-detail', kwargs={'player_id': self.player_profile.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user']['username'], 'player')

    def test_player_view_get_single_player_own(self):
        """Test GET /players/<player_id>/ for player accessing own profile."""
        self.authenticate(self.player_token)
        response = self.client.get(reverse('player-detail', kwargs={'player_id': self.player_profile.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['user']['username'], 'player')

    def test_player_view_post_valid(self):
        """Test POST /players/ for admin."""
        self.authenticate(self.admin_token)
        new_user = CustomUser.objects.create_user(
            username='newplayer', password='new123', email='newplayer@example.com', category='PLAYER'
        )
        data = {
            'user_id': new_user.id,
            'age': 22,
            'type': 'BOWLER',
            'team': self.team.id,
            'is_playing': False
        }
        response = self.client.post(reverse('player-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['age'], 22)
        self.assertEqual(response.data['message'], 'Player created')
        self.assertEqual(response.data['code'], '201')

    def test_player_view_post_captain(self):
        """Test POST /players/ for captain."""
        self.authenticate(self.captain_token)
        new_user = CustomUser.objects.create_user(
            username='newplayer', password='new123', email='newplayer@example.com', category='PLAYER'
        )
        data = {
            'user_id': new_user.id,
            'age': 22,
            'type': 'BOWLER',
            'team': self.team.id,
            'is_playing': False
        }
        response = self.client.post(reverse('player-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['age'], 22)

    def test_player_view_post_invalid(self):
        """Test POST /players/ with invalid data."""
        self.authenticate(self.admin_token)
        data = {
            'user_id': 999,
            'age': 22,
            'type': 'BOWLER',
            'team': self.team.id
        }
        response = self.client.post(reverse('player-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_id', response.data['data'])
        self.assertEqual(response.data['message'], 'Validation failed')
        self.assertEqual(response.data['code'], '400')

    def test_player_view_post_missing_fields(self):
        """Test POST /players/ with missing required fields."""
        self.authenticate(self.admin_token)
        data = {'user_id': self.player_user.id, 'age': 22, 'team': self.team.id}
        response = self.client.post(reverse('player-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('type', response.data['data'])
        self.assertEqual(response.data['message'], 'Validation failed')

    def test_player_view_post_unauthorized(self):
        """Test POST /players/ with player user."""
        self.authenticate(self.player_token)
        data = {
            'user_id': self.player_user.id,
            'age': 22,
            'type': 'BOWLER',
            'team': self.team.id
        }
        response = self.client.post(reverse('player-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['detail'])

    def test_player_view_put_authorized(self):
        """Test PUT /players/<player_id>/ for player updating own profile."""
        self.authenticate(self.player_token)
        data = {'age': 26}
        response = self.client.put(reverse('player-detail', kwargs={'player_id': self.player_profile.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['age'], 26)
        self.assertEqual(response.data['message'], 'Player updated')

    def test_player_view_put_unauthorized(self):
        """Test PUT /players/<player_id>/ for player updating another player's profile."""
        self.authenticate(self.player_token)
        other_user = CustomUser.objects.create_user(
            username='other', password='other123', email='other@example.com', category='PLAYER'
        )
        other_profile = PlayerProfile.objects.create(
            user=other_user, age=30, type='ALL_ROUNDER', team=self.team
        )
        data = {'age': 31}
        response = self.client.put(reverse('player-detail', kwargs={'player_id': other_profile.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['message'], 'Unauthorized')

    def test_player_view_put_admin(self):
        """Test PUT /players/<player_id>/ for admin updating any profile."""
        self.authenticate(self.admin_token)
        data = {'age': 27}
        response = self.client.put(reverse('player-detail', kwargs={'player_id': self.player_profile.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['age'], 27)
        self.assertEqual(response.data['message'], 'Player updated')

    def test_player_view_put_playing_eleven_validation(self):
        """Test PUT /players/<player_id>/ with playing XI validation."""
        for i in range(11):
            user = CustomUser.objects.create_user(
                username=f'player{i}', password='pass123', email=f'player{i}@example.com', category='PLAYER'
            )
            PlayerProfile.objects.create(
                user=user, age=25, type='BATTER', team=self.team, is_playing=True
            )
        self.authenticate(self.admin_token)
        data = {'is_playing': True}
        response = self.client.put(reverse('player-detail', kwargs={'player_id': self.player_profile.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('__all__', response.data['data'])
        self.assertEqual(response.data['message'], 'Validation failed')

    def test_player_view_delete(self):
        """Test DELETE /players/<player_id>/ for admin."""
        self.authenticate(self.admin_token)
        response = self.client.delete(reverse('player-detail', kwargs={'player_id': self.player_profile.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Player deleted')
        self.assertFalse(PlayerProfile.objects.filter(id=self.player_profile.id).exists())

    def test_player_view_delete_unauthorized(self):
        """Test DELETE /players/<player_id>/ for player."""
        self.authenticate(self.player_token)
        response = self.client.delete(reverse('player-detail', kwargs={'player_id': self.player_profile.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['detail'])

    def test_player_view_404(self):
        """Test GET /players/<player_id>/ for non-existent player."""
        self.authenticate(self.admin_token)
        response = self.client.get(reverse('player-detail', kwargs={'player_id': 999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['message'], 'Player not found')
        self.assertEqual(response.data['code'], '404')

    # TeamView Tests
    def test_team_view_get_all(self):
        """Test GET /teams/ for organiser."""
        self.authenticate(self.organiser_token)
        response = self.client.get(reverse('team-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['name'], 'Team A')

    def test_team_view_get_all_paginated(self):
        """Test GET /teams/ with pagination for captain."""
        self.authenticate(self.captain_token)
        response = self.client.get(reverse('team-list'), {'page_size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Team A')

    def test_team_view_get_single(self):
        """Test GET /teams/<team_id>/ for organiser."""
        self.authenticate(self.organiser_token)
        response = self.client.get(reverse('team-detail', kwargs={'team_id': self.team.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['name'], 'Team A')

    def test_team_view_post_valid(self):
        """Test POST /teams/ for organiser."""
        self.authenticate(self.organiser_token)
        data = {'name': 'Team C', 'country': 'England', 'captain': self.captain_user.id}
        response = self.client.post(reverse('team-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['name'], 'Team C')
        self.assertEqual(response.data['message'], 'Team created')

    def test_team_view_post_no_captain(self):
        """Test POST /teams/ without captain."""
        self.authenticate(self.organiser_token)
        data = {'name': 'Team C', 'country': 'England'}
        response = self.client.post(reverse('team-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['name'], 'Team C')
        self.assertIsNone(response.data['data']['captain'])

    def test_team_view_post_invalid_captain(self):
        """Test POST /teams/ with invalid captain."""
        self.authenticate(self.organiser_token)
        data = {'name': 'Team C', 'country': 'England', 'captain': 999}
        response = self.client.post(reverse('team-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('captain', response.data['data'])

    def test_team_view_post_missing_fields(self):
        """Test POST /teams/ with missing required fields."""
        self.authenticate(self.organiser_token)
        data = {'name': 'Team C'}
        response = self.client.post(reverse('team-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('country', response.data['data'])

    def test_team_view_post_unauthorized(self):
        """Test POST /teams/ with player user."""
        self.authenticate(self.player_token)
        data = {'name': 'Team C', 'country': 'England', 'captain': self.captain_user.id}
        response = self.client.post(reverse('team-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['detail'])

    def test_team_view_put(self):
        """Test PUT /teams/<team_id>/ for organiser."""
        self.authenticate(self.organiser_token)
        data = {'name': 'Updated Team A'}
        response = self.client.put(reverse('team-detail', kwargs={'team_id': self.team.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['name'], 'Updated Team A')
        self.assertEqual(response.data['message'], 'Team updated')

    def test_team_view_put_unauthorized(self):
        """Test PUT /teams/<team_id>/ with captain user."""
        self.authenticate(self.captain_token)
        data = {'name': 'Updated Team A'}
        response = self.client.put(reverse('team-detail', kwargs={'team_id': self.team.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['detail'])

    def test_team_view_delete(self):
        """Test DELETE /teams/<team_id>/ for organiser."""
        self.authenticate(self.organiser_token)
        response = self.client.delete(reverse('team-detail', kwargs={'team_id': self.team.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Team deleted')
        self.assertFalse(Team.objects.filter(id=self.team.id).exists())

    def test_team_view_delete_unauthorized(self):
        """Test DELETE /teams/<team_id>/ with player user."""
        self.authenticate(self.player_token)
        response = self.client.delete(reverse('team-detail', kwargs={'team_id': self.team.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['detail'])

    def test_team_view_404(self):
        """Test GET /teams/<team_id>/ for non-existent team."""
        self.authenticate(self.organiser_token)
        response = self.client.get(reverse('team-detail', kwargs={'team_id': 999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['message'], 'Team not found')

    # MatchView Tests
    def test_match_view_get_all_paginated(self):
        """Test GET /matches/ with pagination for organiser."""
        self.authenticate(self.organiser_token)
        response = self.client.get(reverse('match-list'), {'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['venue'], 'Stadium')

    def test_match_view_get_all_empty(self):
        """Test GET /matches/ with no matches."""
        Match.objects.all().delete()
        self.authenticate(self.organiser_token)
        response = self.client.get(reverse('match-list'), {'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 0)

    def test_match_view_get_single(self):
        """Test GET /matches/<match_id>/ for organiser."""
        self.authenticate(self.organiser_token)
        response = self.client.get(reverse('match-detail', kwargs={'match_id': self.match.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['venue'], 'Stadium')

    def test_match_view_post_valid(self):
        """Test POST /matches/ for organiser."""
        self.authenticate(self.organiser_token)
        data = {
            'date': str(date.today()),
            'venue': 'New Stadium',
            'team1': self.team.id,
            'team2': self.team2.id
        }
        response = self.client.post(reverse('match-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['venue'], 'New Stadium')
        self.assertEqual(response.data['message'], 'Match created')

    def test_match_view_post_invalid(self):
        """Test POST /matches/ with invalid data."""
        self.authenticate(self.organiser_token)
        data = {
            'date': str(date.today()),
            'venue': 'New Stadium',
            'team1': 999,
            'team2': self.team2.id
        }
        response = self.client.post(reverse('match-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('team1', response.data['data'])
        self.assertEqual(response.data['message'], 'Validation failed')

    def test_match_view_post_same_teams(self):
        """Test POST /matches/ with same team1 and team2."""
        self.authenticate(self.organiser_token)
        data = {
            'date': str(date.today()),
            'venue': 'New Stadium',
            'team1': self.team.id,
            'team2': self.team.id
        }
        response = self.client.post(reverse('match-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_match_view_post_unauthorized(self):
        """Test POST /matches/ with player user."""
        self.authenticate(self.player_token)
        data = {
            'date': str(date.today()),
            'venue': 'New Stadium',
            'team1': self.team.id,
            'team2': self.team2.id
        }
        response = self.client.post(reverse('match-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['detail'])

    def test_match_view_put(self):
        """Test PUT /matches/<match_id>/ for organiser."""
        self.authenticate(self.organiser_token)
        data = {'venue': 'Updated Stadium', 'winner': self.team.id}
        response = self.client.put(reverse('match-detail', kwargs={'match_id': self.match.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['venue'], 'Updated Stadium')
        self.assertEqual(response.data['message'], 'Match updated')
        self.team.refresh_from_db()
        self.assertEqual(self.team.wins, 1)

    def test_match_view_put_invalid_winner(self):
        """Test PUT /matches/<match_id>/ with invalid winner."""
        self.authenticate(self.organiser_token)
        data = {'venue': 'Updated Stadium', 'winner': 999}
        response = self.client.put(reverse('match-detail', kwargs={'match_id': self.match.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('winner', response.data['data'])

    def test_match_view_put_unauthorized(self):
        """Test PUT /matches/<match_id>/ with player user."""
        self.authenticate(self.player_token)
        data = {'venue': 'Updated Stadium', 'winner': self.team.id}
        response = self.client.put(reverse('match-detail', kwargs={'match_id': self.match.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['detail'])

    def test_match_view_delete(self):
        """Test DELETE /matches/<match_id>/ for organiser."""
        self.authenticate(self.organiser_token)
        response = self.client.delete(reverse('match-detail', kwargs={'match_id': self.match.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Match deleted')
        self.assertFalse(Match.objects.filter(id=self.match.id).exists())

    def test_match_view_delete_unauthorized(self):
        """Test DELETE /matches/<match_id>/ with player user."""
        self.authenticate(self.player_token)
        response = self.client.delete(reverse('match-detail', kwargs={'match_id': self.match.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['detail'])

    def test_match_view_404(self):
        """Test GET /matches/<match_id>/ for non-existent match."""
        self.authenticate(self.organiser_token)
        response = self.client.get(reverse('match-detail', kwargs={'match_id': 999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['message'], 'Match not found')

    # RegisterUserView Tests
    def test_register_user_view_success(self):
        """Test POST /register/ with valid data."""
        data = {
            'username': 'newuser',
            'password': 'Test1234!',
            'password2': 'Test1234!',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'PLAYER'
        }
        response = self.client.post(reverse('user-register'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['username'], 'newuser')
        self.assertEqual(response.data['message'], 'User registered')
        self.assertEqual(response.data['code'], '201')
        user = CustomUser.objects.get(username='newuser')
        self.assertTrue(user.check_password('Test1234!'))
        self.assertEqual(user.category, 'PLAYER')

    def test_register_user_view_password_mismatch(self):
        """Test POST /register/ with mismatched passwords."""
        data = {
            'username': 'newuser',
            'password': 'Test1234!',
            'password2': 'Different1234!',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'PLAYER'
        }
        response = self.client.post(reverse('user-register'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['data'])
        self.assertEqual(response.data['message'], 'Validation failed')
        self.assertEqual(response.data['code'], '400')

    def test_register_user_view_missing_fields(self):
        """Test POST /register/ with missing required fields."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com'
        }
        response = self.client.post(reverse('user-register'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['data'])
        self.assertIn('password2', response.data['data'])
        self.assertIn('category', response.data['data'])
        self.assertEqual(response.data['message'], 'Validation failed')
        self.assertEqual(response.data['code'], '400')

    def test_register_user_view_invalid_email(self):
        """Test POST /register/ with invalid email."""
        data = {
            'username': 'newuser',
            'password': 'Test1234!',
            'password2': 'Test1234!',
            'email': 'invalid-email',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'PLAYER'
        }
        response = self.client.post(reverse('user-register'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['data'])

    def test_register_user_view_invalid_category(self):
        """Test POST /register/ with invalid category."""
        data = {
            'username': 'newuser',
            'password': 'Test1234!',
            'password2': 'Test1234!',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'INVALID'
        }
        response = self.client.post(reverse('user-register'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data['data'])

    def test_register_user_view_duplicate_username(self):
        """Test POST /register/ with duplicate username."""
        data = {
            'username': 'admin',
            'password': 'Test1234!',
            'password2': 'Test1234!',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'PLAYER'
        }
        response = self.client.post(reverse('user-register'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data['data'])

    def test_register_user_view_weak_password(self):
        """Test POST /register/ with weak password."""
        data = {
            'username': 'newuser',
            'password': '123',
            'password2': '123',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'category': 'PLAYER'
        }
        response = self.client.post(reverse('user-register'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['data'])

    # Authentication and Permission Tests
    def test_unauthenticated_access(self):
        """Test access to protected endpoint without JWT."""
        response = self.client.get(reverse('player-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_required_permission(self):
        """Test role_required decorator for unauthorized role (player accessing match creation)."""
        self.authenticate(self.player_token)
        data = {'date': str(date.today()), 'venue': 'Stadium', 'team1': self.team.id, 'team2': self.team2.id}
        response = self.client.post(reverse('match-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Permission denied', response.data['detail'])

    def test_jwt_authentication(self):
        """Test JWT token authentication for protected endpoint."""
        self.authenticate(self.admin_token)
        response = self.client.get(reverse('player-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalidtoken')
        response = self.client.get(reverse('player-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_obtain_pair(self):
        """Test POST /token/ to obtain JWT tokens."""
        data = {'username': 'admin', 'password': 'admin123'}
        response = self.client.post(reverse('token_obtain_pair'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_token_obtain_pair_invalid_credentials(self):
        """Test POST /token/ with invalid credentials."""
        data = {'username': 'admin', 'password': 'wrongpass'}
        response = self.client.post(reverse('token_obtain_pair'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        """Test POST /token/refresh/ to refresh JWT token."""
        refresh = RefreshToken.for_user(self.admin_user)
        data = {'refresh': str(refresh)}
        response = self.client.post(reverse('token_refresh'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_token_refresh_invalid(self):
        """Test POST /token/refresh/ with invalid refresh token."""
        data = {'refresh': 'invalidtoken'}
        response = self.client.post(reverse('token_refresh'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MiddlewareTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = CustomUser.objects.create_user(
            username='admin', password='admin123', email='admin@example.com', category='ADMIN'
        )
        self.admin_token = RefreshToken.for_user(self.admin_user).access_token

    def authenticate(self, token):
        """Helper to set JWT token for authenticated requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_logging_middleware_authenticated(self):
        """Test logging middleware for authenticated requests."""
        self.authenticate(self.admin_token)
        with self.assertLogs('django.request', level='INFO') as log:
            self.client.get(reverse('player-list'))
        self.assertIn("[REQUEST] GET /api/players/ | User: admin (ADMIN)", log.output[0])
        self.assertIn("[RESPONSE] GET /api/players/ | User: admin (ADMIN) | Status: 200 | Error Type: Success", log.output[1])

    def test_logging_middleware_unauthenticated(self):
        """Test logging middleware for unauthenticated requests."""
        with self.assertLogs('django.request', level='INFO') as log:
            self.client.get(reverse('player-list'))
        self.assertIn("[REQUEST] GET /api/players/ | User: Anonymous", log.output[0])
        self.assertIn("[RESPONSE] GET /api/players/ | User: Anonymous | Status: 401 | Error Type: Client Error", log.output[1])

    def test_logging_middleware_post_body(self):
        """Test logging middleware captures POST body."""
        self.authenticate(self.admin_token)
        data = {'name': 'Team C', 'country': 'England'}
        with self.assertLogs('django.request', level='INFO') as log:
            self.client.post(reverse('team-list'), data, format='json')
        self.assertIn("[REQUEST] POST /api/teams/ | User: admin (ADMIN) | Body: {'name': 'Team C', 'country': 'England'}", log.output[0])

    def test_logging_middleware_error(self):
        """Test logging middleware for error responses (404)."""
        self.authenticate(self.admin_token)
        with self.assertLogs('django.request', level='INFO') as log:
            self.client.get(reverse('player-detail', kwargs={'player_id': 999}))
        self.assertIn("[REQUEST] GET /api/players/999/ | User: admin (ADMIN)", log.output[0])
        self.assertIn("[RESPONSE] GET /api/players/999/ | User: admin (ADMIN) | Status: 404 | Error Type: Client Error", log.output[1])


class URLTests(TestCase):
    def test_url_resolving(self):
        """Test that all URLs resolve correctly."""
        self.assertEqual(reverse('user-register'), '/api/register/')
        self.assertEqual(reverse('token_obtain_pair'), '/api/token/')
        self.assertEqual(reverse('token_refresh'), '/api/token/refresh/')
        self.assertEqual(reverse('player-list'), '/api/players/')
        self.assertEqual(reverse('player-detail', kwargs={'player_id': 1}), '/api/players/1/')
        self.assertEqual(reverse('team-list'), '/api/teams/')
        self.assertEqual(reverse('team-detail', kwargs={'team_id': 1}), '/api/teams/1/')
        self.assertEqual(reverse('match-list'), '/api/matches/')
        self.assertEqual(reverse('match-detail', kwargs={'match_id': 1}), '/api/matches/1/')