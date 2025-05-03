from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Team, PlayerProfile, Match

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser  # Adjust import as needed

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'category', 'is_staff')
    list_filter = ('category', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'category')

    fieldsets = UserAdmin.fieldsets + (
        ('User Type', {'fields': ('category',)}),
    )


# Register Team model
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'matches_played', 'wins', 'lost', 'draw', 'points')
    search_fields = ('name', 'country')

# Register PlayerProfile model
@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'age', 'type', 'team', 'matches_played', 'total_runs', 'wickets', 'is_playing')
    list_filter = ('type', 'team', 'is_playing')

# Register Match model
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('team1', 'team2', 'venue', 'date', 'winner')
    list_filter = ('venue', 'date')
