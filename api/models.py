from django.db import models
from django.core.exceptions import ValidationError

class CustomUser(models.Model):
    CATEGORY_CHOICES = [
        ('ADMIN', 'Admin'),
        ('ORGANISER', 'Organiser'),
        ('CAPTAIN', 'Captain'),
        ('PLAYER', 'Player'),
    ]
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='PLAYER')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    def __str__(self):
        return self.username

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
        self.save()

class PlayerProfile(models.Model):
    TYPE_CHOICES = [
        ('BATTER', 'Batter'),
        ('BOWLER', 'Bowler'),
        ('ALL_ROUNDER', 'All-Rounder'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    age = models.PositiveIntegerField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    team = models.ForeignKey(Team, related_name='players', on_delete=models.SET_NULL, null=True, blank=True)
    matches_played = models.PositiveIntegerField(default=0)
    total_runs = models.PositiveIntegerField(default=0)
    wickets = models.PositiveIntegerField(default=0)
    is_playing = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.team.name if self.team else 'No Team'}"

    def clean(self):
        if self.is_playing and self.team:
            playing_count = self.team.players.filter(is_playing=True).count()
            if playing_count >= 11:
                raise ValidationError("A team cannot have more than 11 players in the playing XI.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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

        # Revert previous stats if updating an existing match
        if not is_new:
            try:
                old_match = Match.objects.get(pk=self.pk)
                # Revert team stats based on previous match result
                if old_match.winner:
                    old_match.winner.wins -= 1
                    if old_match.winner == old_match.team1:
                        old_match.team2.lost -= 1
                    else:
                        old_match.team1.lost -= 1
                    old_match.winner.save()
                else:
                    # Previous match was a draw
                    old_match.team1.draw -= 1
                    old_match.team2.draw -= 1
                    old_match.team1.save()
                    old_match.team2.save()
                # Ensure reverted stats are saved
                old_match.team1.save()
                old_match.team2.save()
            except Match.DoesNotExist:
                pass  # Rare case: old match not found

        # Save the match object
        super().save(*args, **kwargs)

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

        # Update team points
        self.team1.update_points()
        self.team2.update_points()