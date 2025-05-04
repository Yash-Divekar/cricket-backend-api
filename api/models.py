from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class CustomUser(AbstractUser):
    CATEGORY_CHOICES = (
        ('PLAYER', 'Player'),
        ('CAPTAIN', 'Captain'),
        ('ADMIN', 'Admin'),
        ('ORGANISER', 'Organiser'),
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='PLAYER')
    email = models.EmailField(unique=True)

    def clean(self):
        if self.category not in dict(self.CATEGORY_CHOICES).keys():
            raise ValidationError({'category': 'Invalid category.'})

    def __str__(self):
        return f"{self.username} ({self.category})"

class Team(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    captain = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='captained_team', limit_choices_to={'category': 'CAPTAIN'}
    )
    matches_played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    lost = models.IntegerField(default=0)
    draw = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def update_points(self):
        """Update team points based on wins and draws."""
        self.points = (self.wins * 2) + self.draw
        self.save()

    def clean(self):
        if self.captain and self.captain.category != 'CAPTAIN':
            raise ValidationError({'captain': 'Captain must have category CAPTAIN.'})
        if self.captain:
            existing_team = Team.objects.filter(captain=self.captain).exclude(id=self.id)
            if existing_team.exists():
                raise ValidationError({'captain': 'This user is already the captain of another team.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        old_captain = None
        if self.pk:
            old_team = Team.objects.get(pk=self.pk)
            old_captain = old_team.captain

        super().save(*args, **kwargs)

        if old_captain and old_captain != self.captain:
            old_captain.category = 'PLAYER'
            old_captain.save()

    def __str__(self):
        return self.name

class PlayerProfile(models.Model):
    PLAYER_TYPES = (
        ('BATTER', 'Batter'),
        ('BOWLER', 'Bowler'),
        ('ALL_ROUNDER', 'All-Rounder'),
    )
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='player_profile')
    age = models.IntegerField()
    type = models.CharField(max_length=20, choices=PLAYER_TYPES)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    matches_played = models.IntegerField(default=0)
    total_runs = models.IntegerField(default=0)
    wickets = models.IntegerField(default=0)
    is_playing = models.BooleanField(default=False)

    def clean(self):
        if self.user.category != 'PLAYER':
            raise ValidationError({'user': 'User must have category PLAYER.'})
        if self.is_playing and self.team.players.filter(is_playing=True).count() >= 11:
            raise ValidationError("A team can only have 11 players in the playing XI.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.type})"

class Match(models.Model):
    date = models.DateField()
    venue = models.CharField(max_length=100)
    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches_as_team1')
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='matches_as_team2')
    winner = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name='matches_won')

    def save(self, *args, **kwargs):
        """
        Save the Match instance, updating team and player stats atomically.
        For new matches: Increment matches_played for teams and playing players, update wins/losses/draws.
        For updates: Revert previous stats, then apply new stats.
        """
        with transaction.atomic():
            # Determine if this is a new match or an update
            is_new = self.pk is None
            old_match = None
            old_winner = None
            old_team1_players = []
            old_team2_players = []

            if not is_new:
                # Fetch previous state for reversion
                old_match = Match.objects.select_related('team1', 'team2', 'winner').get(pk=self.pk)
                old_winner = old_match.winner
                # Get players who were playing in the previous match
                old_team1_players = list(old_match.team1.players.filter(is_playing=True))
                old_team2_players = list(old_match.team2.players.filter(is_playing=True))

            # Save the match to get a PK (needed for new matches)
            super().save(*args, **kwargs)

            # Revert previous stats if updating
            if not is_new:
                # Revert matches_played for teams
                old_match.team1.matches_played = max(0, old_match.team1.matches_played - 1)
                old_match.team2.matches_played = max(0, old_match.team2.matches_played - 1)

                # Revert matches_played for players
                for player in old_team1_players + old_team2_players:
                    player.matches_played = max(0, player.matches_played - 1)
                    player.save()

                # Revert winner or draw stats
                if old_winner:
                    old_winner.wins = max(0, old_winner.wins - 1)
                    loser = old_match.team2 if old_winner == old_match.team1 else old_match.team1
                    loser.lost = max(0, loser.lost - 1)
                    old_winner.update_points()
                    loser.update_points()
                    old_winner.save()
                    loser.save()
                else:
                    # Revert draw
                    old_match.team1.draw = max(0, old_match.team1.draw - 1)
                    old_match.team2.draw = max(0, old_match.team2.draw - 1)
                    old_match.team1.update_points()
                    old_match.team2.update_points()
                    old_match.team1.save()
                    old_match.team2.save()

            # Apply new stats
            # Increment matches_played for teams
            self.team1.matches_played += 1
            self.team2.matches_played += 1

            # Increment matches_played for playing players
            team1_players = self.team1.players.filter(is_playing=True)
            team2_players = self.team2.players.filter(is_playing=True)
            for player in team1_players:
                player.matches_played += 1
                player.save()
            for player in team2_players:
                player.matches_played += 1
                player.save()

            # Update winner or draw stats
            if self.winner:
                self.winner.wins += 1
                loser = self.team2 if self.winner == self.team1 else self.team1
                loser.lost += 1
                self.winner.update_points()
                loser.update_points()
                self.winner.save()
                loser.save()
            else:
                # Draw
                self.team1.draw += 1
                self.team2.draw += 1
                self.team1.update_points()
                self.team2.update_points()
                self.team1.save()
                self.team2.save()
            self.team1.save()
            self.team2.save()

    def __str__(self):
        return f"{self.team1} vs {self.team2} at {self.venue}"

# Signals for captain management
@receiver(post_delete, sender=Team)
def revert_captain_on_team_delete(sender, instance, **kwargs):
    if instance.captain:
        instance.captain.category = 'PLAYER'
        instance.captain.save()

@receiver(post_save, sender=Team)
def ensure_captain_has_team(sender, instance, **kwargs):
    captains = CustomUser.objects.filter(category='CAPTAIN')
    for captain in captains:
        if not Team.objects.filter(captain=captain).exists():
            captain.category = 'PLAYER'
            captain.save()