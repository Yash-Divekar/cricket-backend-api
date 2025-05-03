import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import CustomUser, Team, PlayerProfile, Match
from faker import Faker
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with fake data'

    def handle(self, *args, **kwargs):
        fake = Faker()
        
        # Create admin user
        admin_user = CustomUser.objects.create_superuser(
            username='admin',
            password='adminpassword',
            email='admin@example.com',
            category='ADMIN'
        )
        self.stdout.write(self.style.SUCCESS('Created admin user'))

        # Create teams (without setting statistics directly)
        teams = []
        for i in range(5):  # Create 5 teams
            team = Team.objects.create(
                name=fake.company(),
                country=fake.country()
                # Let matches update the statistics
            )
            teams.append(team)
        self.stdout.write(self.style.SUCCESS('Created teams'))

        # Create 5 organiser users
        for i in range(5):
            CustomUser.objects.create_user(
                username=f'org_{fake.user_name()}',
                password='password123',
                email=fake.email(),
                category='ORGANISER'
            )
        self.stdout.write(self.style.SUCCESS('Created organiser users'))

        # Create captains (1 per team)
        captains = []
        for i in range(5):
            captain_user = CustomUser.objects.create_user(
                username=f'captain_{fake.user_name()}',
                password='password123',
                email=fake.email(),
                category='CAPTAIN'
            )
            captains.append(captain_user)
            
            # Associate captain with team
            team = teams[i]
            team.captain = captain_user
            team.save()
            
            # Create captain's player profile
            PlayerProfile.objects.create(
                user=captain_user,
                age=random.randint(24, 35),
                type='BATTER',  # Captains are batters
                team=team,
                is_playing=True  # Captain is always in playing XI
                # Let matches update the statistics
            )
        self.stdout.write(self.style.SUCCESS('Created captains'))

        # Create players for each team ensuring each team has at least 11 players
        for team in teams:
            # Calculate how many players we need to add to this team
            # Since captain is already on the team and is_playing=True
            current_players = team.players.filter(is_playing=True).count()
            players_needed = max(0, 11 - current_players)
            
            # Add required number of players to the team
            for _ in range(players_needed):
                player_user = CustomUser.objects.create_user(
                    username=fake.user_name(),
                    password='password123',
                    email=fake.email(),
                    category='PLAYER'
                )
                
                PlayerProfile.objects.create(
                    user=player_user,
                    age=random.randint(18, 35),
                    type=random.choice(['BATTER', 'BOWLER', 'ALL_ROUNDER', 'WICKET_KEEPER']),
                    team=team,
                    is_playing=True  # These players are in playing XI
                    # Let matches update the statistics
                )
            
            # Add some additional players who aren't in the playing XI
            for _ in range(random.randint(3, 7)):
                player_user = CustomUser.objects.create_user(
                    username=fake.user_name(),
                    password='password123',
                    email=fake.email(),
                    category='PLAYER'
                )
                
                PlayerProfile.objects.create(
                    user=player_user,
                    age=random.randint(18, 35),
                    type=random.choice(['BATTER', 'BOWLER', 'ALL_ROUNDER', 'WICKET_KEEPER']),
                    team=team,
                    is_playing=False  # These players are not in playing XI
                    # Let matches update the statistics
                )
        self.stdout.write(self.style.SUCCESS('Created players'))

        # Create match history in chronological order
        # Start date for matches - 6 months ago
        start_date = timezone.now().date() - timedelta(days=180)
        
        # Create 20 matches over the past 6 months
        for i in range(20):
            # Generate a date that's progressively more recent
            match_date = start_date + timedelta(days=i * 9)  # Spaced roughly 9 days apart
            
            # Randomly select two different teams
            team1, team2 = random.sample(teams, 2)
            
            # Determine winner (or draw)
            winner = random.choice([team1, team2, None])
            
            # Create the match - this will update team and player statistics automatically
            match = Match.objects.create(
                date=match_date,
                venue=fake.city(),
                team1=team1,
                team2=team2,
                winner=winner
            )
            
            # Randomly update player statistics for this match
            # Only do this for players who were playing in this match
            for player in team1.players.filter(is_playing=True):
                if player.type in ['BATTER', 'ALL_ROUNDER', 'WICKET_KEEPER']:
                    player.total_runs += random.randint(0, 50)
                if player.type in ['BOWLER', 'ALL_ROUNDER']:
                    player.wickets += random.randint(0, 3)
                player.save()
            
            for player in team2.players.filter(is_playing=True):
                if player.type in ['BATTER', 'ALL_ROUNDER', 'WICKET_KEEPER']:
                    player.total_runs += random.randint(0, 50)
                if player.type in ['BOWLER', 'ALL_ROUNDER']:
                    player.wickets += random.randint(0, 3)
                player.save()

        self.stdout.write(self.style.SUCCESS('Created matches and updated player statistics'))
        
        # Summary of created data
        self.stdout.write(self.style.SUCCESS(f"Created {Team.objects.count()} teams"))
        self.stdout.write(self.style.SUCCESS(f"Created {CustomUser.objects.filter(category='ORGANISER').count()} organisers"))
        self.stdout.write(self.style.SUCCESS(f"Created {CustomUser.objects.filter(category='CAPTAIN').count()} captains"))
        self.stdout.write(self.style.SUCCESS(f"Created {CustomUser.objects.filter(category='PLAYER').count()} players"))
        self.stdout.write(self.style.SUCCESS(f"Created {Match.objects.count()} matches"))
        self.stdout.write(self.style.SUCCESS('Successfully populated the database with fake data!'))