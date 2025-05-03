from rest_framework import serializers
from .models import Team, PlayerProfile, Match
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

CustomUser = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'category']

class TeamSerializer(serializers.ModelSerializer):
    players = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'country', 'matches_played', 'wins', 'lost', 'draw', 'points', 'created_at', 'players'
        ]

class PlayerProfileSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(category='PLAYER'),
        source='user',
        write_only=True
    )
    team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())

    class Meta:
        model = PlayerProfile
        fields = [
            'id', 'user', 'user_id', 'age', 'type', 'team', 'matches_played',
            'total_runs', 'wickets', 'is_playing'
        ]

class MatchSerializer(serializers.ModelSerializer):
    team1 = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    team2 = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    winner = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Match
        fields = ['id', 'date', 'venue', 'team1', 'team2', 'winner']


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name', 'category')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = CustomUser.objects.create_user(**validated_data)
        return user
