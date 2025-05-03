from rest_framework.test import APITestCase
from rest_framework import status
from .models import CustomUser
from .models import Team, PlayerProfile, Match, CustomUser
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import RoleEnum

class TestPlayerView(APITestCase):

    def setUp(self):
        # Create users with different roles
        self.admin_user = CustomUser.objects.create_user(username="admin", password="adminpass")
        self.organiser_user = CustomUser.objects.create_user(username="organiser", password="organiserpass")
        self.captain_user = CustomUser.objects.create_user(username="captain", password="captainpass")
        self.player_user = CustomUser.objects.create_user(username="player", password="playerpass")

        # Assign roles to users
        self.admin_user.category = RoleEnum.ADMIN
        self.organiser_user.category = RoleEnum.ORGANISER
        self.captain_user.category = RoleEnum.CAPTAIN
        self.player_user.category = RoleEnum.PLAYER

        self.admin_user.save()
        self.organiser_user.save()
        self.captain_user.save()
        self.player_user.save()

        # Create a team and assign players
        self.team = Team.objects.create(name="Team 1")
        self.player_profile = PlayerProfile.objects.create(user=self.player_user, team=self.team, age=24)
        self.captain_profile = PlayerProfile.objects.create(user=self.captain_user, team=self.team, age=24)

        # Generate JWT tokens for the users
        self.admin_token = self.get_jwt_token(self.admin_user)
        self.organiser_token = self.get_jwt_token(self.organiser_user)
        self.captain_token = self.get_jwt_token(self.captain_user)
        self.player_token = self.get_jwt_token(self.player_user)

    def get_jwt_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    # Test Player GET functionality (by player ID and all players)
    def test_get_player(self):
        url = '/api/player/'
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = f'/api/player/{self.player_profile.id}/'
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_player_get_permission(self):
        url = f'/api/player/{self.player_profile.id}/'
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.player_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = '/api/player/'
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.player_token}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Test Player POST functionality
    def test_create_player(self):
        url = '/api/player/'
        data = {"user": self.player_user.id, "team": self.team.id}
        response = self.client.post(url, data, HTTP_AUTHORIZATION=f'Bearer {self.organiser_token}')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_player_permission(self):
        url = '/api/player/'
        data = {"user": self.player_user.id, "team": self.team.id}
        response = self.client.post(url, data, HTTP_AUTHORIZATION=f'Bearer {self.player_token}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Test Player PUT functionality
    def test_update_player(self):
        url = f'/api/player/{self.player_profile.id}/'
        data = {"user": self.player_user.id, "team": self.team.id, "bio": "Updated Bio"}
        response = self.client.put(url, data, HTTP_AUTHORIZATION=f'Bearer {self.player_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_player_permission(self):
        url = f'/api/player/{self.player_profile.id}/'
        data = {"bio": "Updated Bio"}
        response = self.client.put(url, data, HTTP_AUTHORIZATION=f'Bearer {self.captain_token}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Test Player DELETE functionality
    def test_delete_player(self):
        url = f'/api/player/{self.player_profile.id}/'
        response = self.client.delete(url, HTTP_AUTHORIZATION=f'Bearer {self.player_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_player_permission(self):
        url = f'/api/player/{self.player_profile.id}/'
        response = self.client.delete(url, HTTP_AUTHORIZATION=f'Bearer {self.captain_token}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestTeamView(APITestCase):

    def setUp(self):
        # Similar setup for teams, users, and authentication tokens
        self.admin_user = CustomUser.objects.create_user(username="admin", password="adminpass")
        self.organiser_user = CustomUser.objects.create_user(username="organiser", password="organiserpass")
        self.admin_user.category = RoleEnum.ADMIN
        self.organiser_user.category = RoleEnum.ORGANISER
        self.admin_user.save()
        self.organiser_user.save()

        self.team = Team.objects.create(name="Team 1")

        self.admin_token = self.get_jwt_token(self.admin_user)
        self.organiser_token = self.get_jwt_token(self.organiser_user)

    def get_jwt_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    # Test Team GET functionality (by team ID and all teams)
    def test_get_team(self):
        url = '/api/team/'
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = f'/api/team/{self.team.id}/'
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Test Team POST functionality
    def test_create_team(self):
        url = '/api/team/'
        data = {"name": "New Team"}
        response = self.client.post(url, data, HTTP_AUTHORIZATION=f'Bearer {self.organiser_token}')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_team_permission(self):
        url = '/api/team/'
        data = {"name": "New Team"}
        response = self.client.post(url, data, HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestMatchView(APITestCase):

    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(username="admin", password="adminpass")
        self.organiser_user = CustomUser.objects.create_user(username="organiser", password="organiserpass")
        self.admin_user.category = RoleEnum.ADMIN
        self.organiser_user.category = RoleEnum.ORGANISER
        self.admin_user.save()
        self.organiser_user.save()

        self.match = Match.objects.create()

        self.admin_token = self.get_jwt_token(self.admin_user)
        self.organiser_token = self.get_jwt_token(self.organiser_user)

    def get_jwt_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    # Test Match GET functionality
    def test_get_match(self):
        url = '/api/match/'
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = f'/api/match/{self.match.id}/'
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Test Match POST functionality
    def test_create_match(self):
        url = '/api/match/'
        data = {"name": "New Match"}
        response = self.client.post(url, data, HTTP_AUTHORIZATION=f'Bearer {self.organiser_token}')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_match_permission(self):
        url = '/api/match/'
        data = {"name": "New Match"}
        response = self.client.post(url, data, HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestCaptainDecidePlaying11View(APITestCase):

    def setUp(self):
        self.captain_user = CustomUser.objects.create_user(username="captain", password="captainpass")
        self.player_user = CustomUser.objects.create_user(username="player", password="playerpass")
        self.captain_user.category = RoleEnum.CAPTAIN
        self.player_user.category = RoleEnum.PLAYER
        self.captain_user.save()
        self.player_user.save()

        self.team = Team.objects.create(name="Team 1")
        self.captain_profile = PlayerProfile.objects.create(user=self.captain_user, team=self.team, age=24)
        self.player_profile = PlayerProfile.objects.create(user=self.player_user, team=self.team, age=24)

        self.captain_token = self.get_jwt_token(self.captain_user)
        self.player_token = self.get_jwt_token(self.player_user)

    def get_jwt_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_decide_playing_11(self):
        url = '/api/captain-decide-playing-11/'
        data = {"team_id": self.team.id, "playing_11": ["Player 1", "Player 2"]}
        response = self.client.post(url, data, HTTP_AUTHORIZATION=f'Bearer {self.captain_token}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_decide_playing_11_permission(self):
        url = '/api/captain-decide-playing-11/'
        data = {"team_id": self.team.id, "playing_11": ["Player 1", "Player 2"]}
        response = self.client.post(url, data, HTTP_AUTHORIZATION=f'Bearer {self.player_token}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
