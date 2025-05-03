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

from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    matches_played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    lost = models.IntegerField(default=0)
    draw = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    captain = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def update_points(self):
        self.points = (self.wins * 2) + self.draw 

    def save(self, *args, **kwargs):
        self.update_points()
        super().save(*args, **kwargs)


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
        
        # Handle updates to existing match
        if not is_new:
            old_match = Match.objects.get(pk=self.pk)
            
            # Revert previous match results from team stats
            if old_match.winner:
                old_match.winner.wins -= 1
                if old_match.winner == old_match.team1:
                    old_match.team2.lost -= 1
                else:
                    old_match.team1.lost -= 1
                old_match.winner.save()
            else:
                # It was a draw previously
                old_match.team1.draw -= 1
                old_match.team2.draw -= 1
                
            # Only save if we're not changing teams (which would be unusual)
            if old_match.team1.id == self.team1.id:
                old_match.team1.save()
            if old_match.team2.id == self.team2.id:
                old_match.team2.save()
                
        # Save the match object first
        super().save(*args, **kwargs)
        
        # Update player match counts only for new matches
        if is_new:
            for player in self.team1.players.filter(is_playing=True):
                player.matches_played += 1
                player.save()

            for player in self.team2.players.filter(is_playing=True):
                player.matches_played += 1
                player.save()
                
            # Increment matches_played only for new matches
            self.team1.matches_played += 1
            self.team2.matches_played += 1

        # Apply new match results to team stats
        if self.winner:
            self.winner.wins += 1
            if self.winner == self.team1:
                self.team2.lost += 1
            else:
                self.team1.lost += 1
        else:
            # It's a draw
            self.team1.draw += 1
            self.team2.draw += 1

        # Save the teams to update their stats
        self.team1.save()
        self.team2.save()