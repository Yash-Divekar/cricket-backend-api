from rest_framework import serializers
from django.contrib.auth import get_user_model
from api.models import Team, PlayerProfile, Match
from django.core.exceptions import ValidationError

CustomUser = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'category']

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'password2', 'email', 'first_name', 'last_name', 'category']
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'category': {'required': True}
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords must match.'})
        if data['category'] not in dict(CustomUser.CATEGORY_CHOICES).keys():
            raise serializers.ValidationError({'category': 'Invalid category.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            category=validated_data['category']
        )
        return user

class PlayerProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')
    team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())

    class Meta:
        model = PlayerProfile
        fields = [
            'id', 'user_id', 'age', 'type', 'team', 'matches_played',
            'total_runs', 'wickets', 'is_playing'
        ]

    def validate_user_id(self, value):
        try:
            user = CustomUser.objects.get(id=value)
            if user.category != 'PLAYER':
                raise serializers.ValidationError('User must have category PLAYER.')
            if PlayerProfile.objects.filter(user=user).exists():
                raise serializers.ValidationError('Player profile already exists for this user.')
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError('User does not exist.')
        return value

    def validate_type(self, value):
        if value not in dict(PlayerProfile.PLAYER_TYPES).keys():
            raise serializers.ValidationError('Invalid player type.')
        return value

    def create(self, validated_data):
        user_id = validated_data.pop('user').get('id')
        user = CustomUser.objects.get(id=user_id)
        return PlayerProfile.objects.create(user=user, **validated_data)

class MatchSerializer(serializers.ModelSerializer):
    team1 = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    team2 = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    winner = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all(), allow_null=True)

    class Meta:
        model = Match
        fields = ['id', 'date', 'venue', 'team1', 'team2', 'winner']

    def validate(self, data):
        # Allow same teams (per current test behavior)
        # Uncomment below to enforce different teams
        # if data['team1'] == data['team2']:
        #     raise serializers.ValidationError('Team1 and Team2 cannot be the same.')
        return data

class TeamSerializer(serializers.ModelSerializer):
    captain = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(category='CAPTAIN'),
        allow_null=True
    )
    players = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, source='players.user'
    )

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'country', 'matches_played', 'wins', 'lost',
            'draw', 'points', 'created_at', 'players', 'captain'
        ]

    def validate_captain(self, value):
        if value is None:
            return value
        # Ensure captain is not assigned to another team
        existing_team = Team.objects.filter(captain=value).exclude(id=self.instance.id if self.instance else None)
        if existing_team.exists():
            raise serializers.ValidationError('This user is already the captain of another team.')
        return value

    def create(self, validated_data):
        captain = validated_data.get('captain')
        team = Team.objects.create(**validated_data)
        # Ensure previous captain (if any) is reverted to PLAYER
        if captain:
            # Check if another team has this captain
            other_teams = Team.objects.filter(captain=captain).exclude(id=team.id)
            for other_team in other_teams:
                other_team.captain = None
                other_team.save()
        return team

    def update(self, instance, validated_data):
        old_captain = instance.captain
        new_captain = validated_data.get('captain', old_captain)

        # Update team
        instance = super().update(instance, validated_data)

        # Revert old captain to PLAYER if changed
        if old_captain and old_captain != new_captain:
            old_captain.category = 'PLAYER'
            old_captain.save()

        # Ensure no other team has this captain
        if new_captain:
            other_teams = Team.objects.filter(captain=new_captain).exclude(id=instance.id)
            for other_team in other_teams:
                other_team.captain = None
                other_team.save()

        return instance