from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings

class CustomUser(AbstractUser):
    CATEGORY_CHOICES = [
        ('ADMIN', 'Admin'),
        ('ORGANISER', 'Organiser'),
        ('CAPTAIN', 'Captain'),
        ('PLAYER', 'Player'),
    ]
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)

    def __str__(self):
        return f"{self.username} ({self.category})"

    def clean(self):
        if self.category not in dict(self.CATEGORY_CHOICES).keys():
            raise ValidationError({'category': 'Invalid category.'})
        
class Team(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    captain = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    matches_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    lost = models.PositiveIntegerField(default=0)
    draw = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def update_points(self):
        self.points = (self.wins * 2) + self.draw

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save first to ensure the instance exists
        self.update_points()  # Recalculate points
        super().save(update_fields=['points'])  # Save again to update points

class PlayerProfile(models.Model):
    PLAYER_TYPES = [
        ('BATTER', 'Batter'),
        ('BOWLER', 'Bowler'),
        ('ALL_ROUNDER', 'All-Rounder'),
        ('WICKET_KEEPER', 'Wicket-Keeper'),
    ]

    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE, related_name='playerprofile')
    age = models.IntegerField()
    type = models.CharField(max_length=20, choices=PLAYER_TYPES, default='BATTER')
    team = models.ForeignKey(Team, related_name='players', on_delete=models.CASCADE)
    matches_played = models.IntegerField(default=0)
    total_runs = models.IntegerField(default=0)
    wickets = models.IntegerField(default=0)
    is_playing = models.BooleanField(default=False)

    def clean(self):
        if self.is_playing:
            playing_eleven_count = PlayerProfile.objects.filter(team=self.team, is_playing=True).exclude(pk=self.pk).count()
            if playing_eleven_count >= 11:
                raise ValidationError("A team can only have 11 players in the playing XI.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.type})"
    
class Match(models.Model):
    date = models.DateField()
    venue = models.CharField(max_length=200)
    team1 = models.ForeignKey(Team, related_name='team1', on_delete=models.CASCADE)
    team2 = models.ForeignKey(Team, related_name='team2', on_delete=models.CASCADE)
    winner = models.ForeignKey(Team, related_name='Match_won', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.team1} vs {self.team2} at {self.venue}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        # Store old match state for reversion if updating
        old_winner = None
        old_team1 = None
        old_team2 = None
        if not is_new:
            try:
                old_match = Match.objects.get(pk=self.pk)
                old_winner = old_match.winner
                old_team1 = old_match.team1
                old_team2 = old_match.team2
            except Match.DoesNotExist:
                pass  

        # Revert previous stats if updating
        if not is_new and old_winner:
            old_winner.wins = max(0, old_winner.wins - 1)
            old_winner.update_points()
            old_winner.save()
            if old_winner == old_team1:
                old_team2.lost = max(0, old_team2.lost - 1)
                old_team2.save()
            else:
                old_team1.lost = max(0, old_team1.lost - 1)
                old_team1.save()
        elif not is_new and not old_winner:
            old_team1.draw = max(0, old_team1.draw - 1)
            old_team2.draw = max(0, old_team2.draw - 1)
            old_team1.save()
            old_team2.save()

        # Update player and team match counts only for new matches
        if is_new:
            for player in self.team1.players.filter(is_playing=True):
                player.matches_played += 1
                player.save()
            for player in self.team2.players.filter(is_playing=True):
                player.matches_played += 1
                player.save()
            self.team1.matches_played += 1
            self.team2.matches_played += 1
            self.team1.save()
            self.team2.save()

        # Apply new match results
        if self.winner:
            self.winner.wins += 1
            self.winner.update_points()
            self.winner.save()
            if self.winner == self.team1:
                self.team2.lost += 1
                self.team2.save()
            else:
                self.team1.lost += 1
                self.team1.save()
        else:
            self.team1.draw += 1
            self.team2.draw += 1
            self.team1.save()
            self.team2.save()

        # Save the match object after all stats are updated
        super().save(*args, **kwargs)        
            
            