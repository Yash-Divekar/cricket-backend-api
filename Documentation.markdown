# Cricket Backend API Documentation

## Overview
The **Cricket Backend API** is a RESTful API designed to manage cricket-related data for a sports application. It supports functionalities such as user registration, team and player management, and match tracking. The API is built with **Django REST Framework (DRF)** and uses **JWT (JSON Web Token)** authentication for secure access. It enforces role-based permissions for different user categories: **ADMIN**, **ORGANISER**, **CAPTAIN**, and **PLAYER**.

### Key Features
- **User Management**: Register and authenticate users with specific roles.
- **Team Management**: Create, update, and delete teams with captains and players.
- **Player Profiles**: Manage player details, including type (e.g., BATTER, BOWLER) and playing status.
- **Match Tracking**: Record match details, including teams, winners, and statistics.
- **Role-Based Access**: Restrict actions based on user roles (e.g., only ORGANISER can create matches).
- **Pagination**: Support for paginated responses in list endpoints.

**Base URL**: `/api/`  
**Content Type**: `application/json`  
**Current Version**: 1.0.0 (as of May 04, 2025)

## Architecture
The API is built using a modular, scalable architecture with the following components:

### Tech Stack
- **Framework**: Django 4.x with Django REST Framework
- **Authentication**: `rest_framework_simplejwt` for JWT-based authentication
- **Database**: PostgreSQL (assumed, based on Django’s default ORM)
- **Logging**: Custom middleware (`log_requests.py`) for request/response logging
- **Testing**: Django’s test framework with `coverage` (91% coverage)
- **Python Version**: 3.8+ (based on `myenv` virtual environment)

### Project Structure
```
cricket_api/
├── api/
│   ├── migrations/        # Database migrations
│   ├── __init__.py
│   ├── admin.py          # Django admin configuration
│   ├── apps.py           # App configuration
│   ├── middleware/       # Custom middleware (log_requests.py)
│   ├── models.py         # Database models (CustomUser, Team, PlayerProfile, Match)
│   ├── permissions.py    # Custom role-based permissions
│   ├── serializers.py    # DRF serializers for data validation/serialization
│   ├── tests.py          # Test suite (92 tests)
│   ├── urls.py           # API endpoint routing
│   ├── utils.py          # Utility functions
│   ├── views.py          # API views and logic
├── cricket_api/
│   ├── __init__.py
│   ├── settings.py       # Django settings (e.g., JWT configuration)
│   ├── urls.py           # Root URL configuration
├── manage.py             # Django management script
```

### Authentication Logic
- **JWT Authentication**: Users obtain an access token via `/api/token/` by providing username and password. The token is included in the `Authorization` header as `Bearer <token>` for protected endpoints.
- **Role-Based Permissions**: Custom permissions (likely in `permissions.py`) enforce role-specific access using a `@role_required` decorator or similar. For example:
  - ADMIN: Full access to all resources.
  - ORGANISER: Manage teams and matches.
  - CAPTAIN: Manage team players.
  - PLAYER: View own profile and team details.
- **Anonymous User Issue**: Test logs show all requests as `Anonymous`, indicating authentication is not applied in tests. This is addressed in the **Troubleshooting** section.

### Business Logic
- **User Registration**: Validates username, email, password, and role (`category`). Passwords must match and meet strength requirements.
- **Team Management**: Ensures a captain is unique per team and reverts to PLAYER role when unassigned or team is deleted.
- **Player Profiles**: Enforces a maximum of 11 players in a team’s playing XI. Players must have a `PLAYER` role.
- **Matches**: Updates team and player statistics (e.g., matches played, wins, points) on save. Validates that the winner is either `team1` or `team2`.

## Database Schema
The database schema is inferred from `tests.py` and `models.py` references. It consists of four main models with the following fields and relationships:

### CustomUser
- **Fields**:
  - `id` (Primary Key, AutoField)
  - `username` (CharField, unique)
  - `email` (EmailField, optional)
  - `password` (CharField)
  - `first_name` (CharField, optional)
  - `last_name` (CharField, optional)
  - `category` (CharField, choices: ADMIN, ORGANISER, CAPTAIN, PLAYER)
  - `is_staff` (BooleanField, default: False)
  - `is_superuser` (BooleanField, default: False)
- **Constraints**:
  - `category` must be one of the defined choices.
  - `username` and `email` (if provided) must be unique.
- **Methods**:
  - `__str__`: Returns `username (category)`.

### Team
- **Fields**:
  - `id` (Primary Key, AutoField)
  - `name` (CharField)
  - `country` (CharField)
  - `captain` (ForeignKey to CustomUser, nullable)
  - `matches_played` (IntegerField, default: 0)
  - `wins` (IntegerField, default: 0)
  - `lost` (IntegerField, default: 0)
  - `draw` (IntegerField, default: 0)
  - `points` (IntegerField, default: 0)
  - `created_at` (DateTimeField, auto_now_add)
- **Relationships**:
  - One-to-one with `captain` (CustomUser with `category=CAPTAIN`).
  - Many-to-many with `PlayerProfile` (via `team` field in PlayerProfile).
- **Constraints**:
  - A captain can only be assigned to one team.
  - Captain reverts to PLAYER when unassigned or team is deleted.
- **Methods**:
  - `update_points`: Calculates points as `(wins * 2) + draw`.
  - `__str__`: Returns `name`.

### PlayerProfile
- **Fields**:
  - `id` (Primary Key, AutoField)
  - `user` (OneToOneField to CustomUser)
  - `age` (IntegerField)
  - `type` (CharField, choices: BATTER, BOWLER, ALL_ROUNDER)
  - `team` (ForeignKey to Team)
  - `matches_played` (IntegerField, default: 0)
  - `total_runs` (IntegerField, default: 0)
  - `wickets` (IntegerField, default: 0)
  - `is_playing` (BooleanField, default: False)
- **Constraints**:
  - `user` must have `category=PLAYER`.
  - A team can have up to 11 players with `is_playing=True`.
  - `team` is required.
- **Methods**:
  - `clean`: Validates playing XI limit.
  - `__str__`: Returns `username (type)`.

### Match
- **Fields**:
  - `id` (Primary Key, AutoField)
  - `date` (DateField)
  - `venue` (CharField)
  - `team1` (ForeignKey to Team)
  - `team2` (ForeignKey to Team)
  - `winner` (ForeignKey to Team, nullable)
- **Relationships**:
  - Foreign keys to `team1`, `team2`, and `winner` (Team).
- **Constraints**:
  - `winner` must be either `team1` or `team2` (if set).
- **Methods**:
  - `save`: Updates team and player statistics (e.g., matches played, wins, losses, draws, points).
  - `clean`: Validates winner constraint.
  - `__str__`: Returns `team1 vs team2 at venue`.

### Schema Notes
- **Transactions**: `Match.save` uses `transaction.atomic()` to ensure data consistency when updating statistics.
- **Validation**: Models use `full_clean()` to enforce constraints (e.g., captain uniqueness, playing XI limit).
- **Relationships**: Managed via Django ORM, with cascading deletes (e.g., team deletion affects captain role).

## API Endpoints
All endpoints use the `/api/` base URL and expect `application/json` content type. Most require JWT authentication via the `Authorization: Bearer <token>` header, except `/api/register/`.

### Authentication Endpoints
#### `POST /api/token/`
**Description**: Obtain a JWT access and refresh token pair.  
**Authentication**: None.  
**Permissions**: None.  
**Request Body**:
```json
{
    "username": "string",
    "password": "string"
}
```
**Responses**:
- **200 OK**:
  ```json
  {
      "refresh": "string",
      "access": "string"
  }
  ```
- **401 Unauthorized**:
  ```json
  {
      "detail": "No active account found with the given credentials"
  }
  ```
**Example**:
```bash
curl -X POST /api/token/ \
-H "Content-Type: application/json" \
-d '{"username": "admin", "password": "admin123"}'
```

#### `POST /api/token/refresh/`
**Description**: Refresh an access token using a refresh token.  
**Authentication**: None.  
**Permissions**: None.  
**Request Body**:
```json
{
    "refresh": "string"
}
```
**Responses**:
- **200 OK**:
  ```json
  {
      "access": "string"
  }
  ```
- **401 Unauthorized**:
  ```json
  {
      "detail": "Token is invalid or expired"
  }
  ```
**Example**:
```bash
curl -X POST /api/token/refresh/ \
-H "Content-Type: application/json" \
-d '{"refresh": "your_refresh_token"}'
```

### User Registration
#### `POST /api/register/`
**Description**: Register a new user with a specific role.  
**Authentication**: None.  
**Permissions**: None.  
**Request Body**:
```json
{
    "username": "string",
    "password": "string",
    "password2": "string",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "category": "string" // ADMIN, ORGANISER, CAPTAIN, PLAYER
}
```
**Responses**:
- **201 Created**:
  ```json
  {
      "data": {
          "username": "newuser",
          "email": "newuser@example.com",
          "category": "PLAYER"
      },
      "message": "User registered",
      "code": "201"
  }
  ```
- **400 Bad Request**:
  ```json
  {
      "data": {
          "password": ["Passwords do not match"],
          "email": ["Enter a valid email address"],
          "category": ["'INVALID' is not a valid choice"]
      },
      "message": "Validation failed",
      "code": "400"
  }
  ```
**Example**:
```bash
curl -X POST /api/register/ \
-H "Content-Type: application/json" \
-d '{
    "username": "newuser",
    "password": "Test1234!",
    "password2": "Test1234!",
    "email": "newuser@example.com",
    "first_name": "New",
    "last_name": "User",
    "category": "PLAYER"
}'
```

### Players
#### `GET /api/players/`
**Description**: Retrieve a paginated list of player profiles.  
**Authentication**: JWT Bearer token.  
**Permissions**: ADMIN, ORGANISER, CAPTAIN, PLAYER (PLAYER limited to own team).  
**Query Parameters**:
- `page_size` (optional, integer): Results per page (e.g., `5`).
**Responses**:
- **200 OK**:
  ```json
  {
      "count": 1,
      "next": null,
      "previous": null,
      "results": [
          {
              "id": 1,
              "user": {
                  "id": 4,
                  "username": "player",
                  "email": "player@example.com",
                  "category": "PLAYER"
              },
              "age": 25,
              "type": "BATTER",
              "team": 1,
              "is_playing": true,
              "matches_played": 0,
              "total_runs": 0,
              "wickets": 0
          }
      ]
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
**Example**:
```bash
curl -X GET /api/players/?page_size=5 \
-H "Authorization: Bearer your_access_token"
```

#### `GET /api/players/{player_id}/`
**Description**: Retrieve a single player profile.  
**Authentication**: JWT Bearer token.  
**Permissions**: ADMIN, ORGANISER, CAPTAIN, PLAYER (PLAYER limited to own profile or team).  
**Path Parameters**:
- `player_id` (integer): Player profile ID.
**Responses**:
- **200 OK**:
  ```json
  {
      "data": {
          "id": 1,
          "user": {
              "id": 4,
              "username": "player",
              "email": "player@example.com",
              "category": "PLAYER"
          },
          "age": 25,
          "type": "BATTER",
          "team": 1,
          "is_playing": true,
          "matches_played": 0,
          "total_runs": 0,
          "wickets": 0
      },
      "message": "Success",
      "code": "200"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "message": "Unauthorized",
      "code": "403"
  }
  ```
- **404 Not Found**:
  ```json
  {
      "message": "Player not found",
      "code": "404"
  }
  ```
**Example**:
```bash
curl -X GET /api/players/1/ \
-H "Authorization: Bearer your_access_token"
```

#### `POST /api/players/`
**Description**: Create a new player profile.  
**Authentication**: JWT Bearer token.  
**Permissions**: ADMIN, CAPTAIN.  
**Request Body**:
```json
{
    "user_id": integer,
    "age": integer,
    "type": "string", // BATTER, BOWLER, ALL_ROUNDER
    "team": integer,
    "is_playing": boolean
}
```
**Responses**:
- **201 Created**:
  ```json
  {
      "data": {
          "id": 2,
          "user_id": 5,
          "age": 22,
          "type": "BOWLER",
          "team": 1,
          "is_playing": false,
          "matches_played": 0,
          "total_runs": 0,
          "wickets": 0
      },
      "message": "Player created",
      "code": "201"
  }
  ```
- **400 Bad Request**:
  ```json
  {
      "data": {
          "user_id": ["User does not exist"],
          "type": ["'INVALID' is not a valid choice"]
      },
      "message": "Validation failed",
      "code": "400"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
**Example**:
```bash
curl -X POST /api/players/ \
-H "Authorization: Bearer your_access_token" \
-H "Content-Type: application/json" \
-d '{
    "user_id": 5,
    "age": 22,
    "type": "BOWLER",
    "team": 1,
    "is_playing": false
}'
```

#### `PUT /api/players/{player_id}/`
**Description**: Update a player profile.  
**Authentication**: JWT Bearer token.  
**Permissions**: ADMIN, CAPTAIN, PLAYER (own profile).  
**Path Parameters**:
- `player_id` (integer): Player profile ID.
**Request Body**:
```json
{
    "age": integer, // Optional
    "type": "string", // Optional: BATTER, BOWLER, ALL_ROUNDER
    "team": integer, // Optional
    "is_playing": boolean // Optional
}
```
**Responses**:
- **200 OK**:
  ```json
  {
      "data": {
          "id": 1,
          "user_id": 4,
          "age": 26,
          "type": "BATTER",
          "team": 1,
          "is_playing": true,
          "matches_played": 0,
          "total_runs": 0,
          "wickets": 0
      },
      "message": "Player updated",
      "code": "200"
  }
  ```
- **400 Bad Request**:
  ```json
  {
      "data": {
          "__all__": ["A team can only have 11 players in the playing XI"]
      },
      "message": "Validation failed",
      "code": "400"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "message": "Unauthorized",
      "code": "403"
  }
  ```
- **404 Not Found**:
  ```json
  {
      "message": "Player not found",
      "code": "404"
  }
  ```
**Example**:
```bash
curl -X PUT /api/players/1/ \
-H "Authorization: Bearer your_access_token" \
-H "Content-Type: application/json" \
-d '{"age": 26}'
```

#### `DELETE /api/players/{player_id}/`
**Description**: Delete a player profile.  
**Authentication**: JWT Bearer token.  
**Permissions**: ADMIN.  
**Path Parameters**:
- `player_id` (integer): Player profile ID.
**Responses**:
- **200 OK**:
  ```json
  {
      "message": "Player deleted",
      "code": "200"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
- **404 Not Found**:
  ```json
  {
      "message": "Player not found",
      "code": "404"
  }
  ```
**Example**:
```bash
curl -X DELETE /api/players/1/ \
-H "Authorization: Bearer your_access_token"
```

### Teams
#### `GET /api/teams/`
**Description**: Retrieve a paginated list of teams.  
**Authentication**: JWT Bearer token.  
**Permissions**: ADMIN, ORGANISER, CAPTAIN, PLAYER.  
**Query Parameters**:
- `page_size` (optional, integer): Results per page (e.g., `1`).
**Responses**:
- **200 OK**:
  ```json
  {
      "count": 2,
      "next": null,
      "previous": null,
      "results": [
          {
              "id": 1,
              "name": "Team A",
              "country": "India",
              "matches_played": 0,
              "wins": 0,
              "lost": 0,
              "draw": 0,
              "points": 0,
              "created_at": "2025-05-04T10:37:41.327096Z",
              "players": [4],
              "captain": 3
          }
      ]
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
**Example**:
```bash
curl -X GET /api/teams/?page_size=1 \
-H "Authorization: Bearer your_access_token"
```

#### `GET /api/teams/{team_id}/`
**Description**: Retrieve a single team.  
**Authentication**: JWT Bearer token.  
**Permissions**: ADMIN, ORGANISER, CAPTAIN, PLAYER.  
**Path Parameters**:
- `team_id` (integer): Team ID.
**Responses**:
- **200 OK**:
  ```json
  {
      "data": {
          "id": 1,
          "name": "Team A",
          "country": "India",
          "matches_played": 0,
          "wins": 0,
          "lost": 0,
          "draw": 0,
          "points": 0,
          "created_at": "2025-05-04T10:37:41.327096Z",
          "players": [4],
          "captain": 3
      },
      "message": "Success",
      "code": "200"
  }
  ```
- **404 Not Found**:
  ```json
  {
      "message": "Team not found",
      "code": "404"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
**Example**:
```bash
curl -X GET /api/teams/1/ \
-H "Authorization: Bearer your_access_token"
```

#### `POST /api/teams/`
**Description**: Create a new team.  
**Authentication**: JWT Bearer token.  
**Permissions**: ORGANISER.  
**Request Body**:
```json
{
    "name": "string",
    "country": "string",
    "captain": integer // Optional, must be CAPTAIN
}
```
**Responses**:
- **201 Created**:
  ```json
  {
      "data": {
          "id": 3,
          "name": "Team C",
          "country": "England",
          "matches_played": 0,
          "wins": 0,
          "lost": 0,
          "draw": 0,
          "points": 0,
          "created_at": "2025-05-04T10:37:41.327096Z",
          "players": [],
          "captain": 5
      },
      "message": "Team created",
      "code": "201"
  }
  ```
- **400 Bad Request**:
  ```json
  {
      "data": {
          "captain": ["This user is already a captain"],
          "country": ["This field is required"]
      },
      "message": "Validation failed",
      "code": "400"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
**Example**:
```bash
curl -X POST /api/teams/ \
-H "Authorization: Bearer your_access_token" \
-H "Content-Type: application/json" \
-d '{
    "name": "Team C",
    "country": "England",
    "captain": 5
}'
```

#### `PUT /api/teams/{team_id}/`
**Description**: Update a team.  
**Authentication**: JWT Bearer token.  
**Permissions**: ORGANISER.  
**Path Parameters**:
- `team_id` (integer): Team ID.
**Request Body**:
```json
{
    "name": "string", // Optional
    "country": "string", // Optional
    "captain": integer // Optional
}
```
**Responses**:
- **200 OK**:
  ```json
  {
      "data": {
          "id": 1,
          "name": "Updated Team A",
          "country": "India",
          "matches_played": 0,
          "wins": 0,
          "lost": 0,
          "draw": 0,
          "points": 0,
          "created_at": "2025-05-04T10:37:41.327096Z",
          "players": [4],
          "captain": 3
      },
      "message": "Team updated",
      "code": "200"
  }
  ```
- **400 Bad Request**:
  ```json
  {
      "data": {
          "captain": ["Invalid captain"]
      },
      "message": "Validation failed",
      "code": "400"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
- **404 Not Found**:
  ```json
  {
      "message": "Team not found",
      "code": "404"
  }
  ```
**Example**:
```bash
curl -X PUT /api/teams/1/ \
-H "Authorization: Bearer your_access_token" \
-H "Content-Type: application/json" \
-d '{"name": "Updated Team A"}'
```

#### `DELETE /api/teams/{team_id}/`
**Description**: Delete a team.  
**Authentication**: JWT Bearer token.  
**Permissions**: ORGANISER.  
**Path Parameters**:
- `team_id` (integer): Team ID.
**Responses**:
- **200 OK**:
  ```json
  {
      "message": "Team deleted",
      "code": "200"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
- **404 Not Found**:
  ```json
  {
      "message": "Team not found",
      "code": "404"
  }
  ```
**Example**:
```bash
curl -X DELETE /api/teams/1/ \
-H "Authorization: Bearer your_access_token"
```

### Matches
#### `GET /api/matches/`
**Description**: Retrieve a paginated list of matches.  
**Authentication**: JWT Bearer token.  
**Permissions**: ORGANISER, ADMIN.  
**Query Parameters**:
- `page_size` (optional, integer): Results per page (e.g., `5`).
**Responses**:
- **200 OK**:
  ```json
  {
      "count": 1,
      "next": null,
      "previous": null,
      "results": [
          {
              "id": 1,
              "date": "2025-05-04",
              "venue": "Stadium",
              "team1": 1,
              "team2": 2,
              "winner": null
          }
      ]
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
**Example**:
```bash
curl -X GET /api/matches/?page_size=5 \
-H "Authorization: Bearer your_access_token"
```

#### `GET /api/matches/{match_id}/`
**Description**: Retrieve a single match.  
**Authentication**: JWT Bearer token.  
**Permissions**: ORGANISER, ADMIN.  
**Path Parameters**:
- `match_id` (integer): Match ID.
**Responses**:
- **200 OK**:
  ```json
  {
      "data": {
          "id": 1,
          "date": "2025-05-04",
          "venue": "Stadium",
          "team1": 1,
          "team2": 2,
          "winner": null
      },
      "message": "Success",
      "code": "200"
  }
  ```
- **404 Not Found**:
  ```json
  {
      "message": "Match not found",
      "code": "404"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
**Example**:
```bash
curl -X GET /api/matches/1/ \
-H "Authorization: Bearer your_access_token"
```

#### `POST /api/matches/`
**Description**: Create a new match.  
**Authentication**: JWT Bearer token.  
**Permissions**: ORGANISER.  
**Request Body**:
```json
{
    "date": "string", // YYYY-MM-DD
    "venue": "string",
    "team1": integer,
    "team2": integer,
    "winner": integer // Optional
}
```
**Responses**:
- **201 Created**:
  ```json
  {
      "data": {
          "id": 2,
          "date": "2025-05-04",
          "venue": "New Stadium",
          "team1": 1,
          "team2": 2,
          "winner": 1
      },
      "message": "Match created",
      "code": "201"
  }
  ```
- **400 Bad Request**:
  ```json
  {
      "data": {
          "team1": ["Team does not exist"],
          "winner": ["Winner must be team1 or team2"]
      },
      "message": "Validation failed",
      "code": "400"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
**Example**:
```bash
curl -X POST /api/matches/ \
-H "Authorization: Bearer your_access_token" \
-H "Content-Type: application/json" \
-d '{
    "date": "2025-05-04",
    "venue": "New Stadium",
    "team1": 1,
    "team2": 2,
    "winner": 1
}'
```

#### `PUT /api/matches/{match_id}/`
**Description**: Update a match.  
**Authentication**: JWT Bearer token.  
**Permissions**: ORGANISER.  
**Path Parameters**:
- `match_id` (integer): Match ID.
**Request Body**:
```json
{
    "date": "string", // Optional: YYYY-MM-DD
    "venue": "string", // Optional
    "team1": integer, // Optional
    "team2": integer, // Optional
    "winner": integer // Optional
}
```
**Responses**:
- **200 OK**:
  ```json
  {
      "data": {
          "id": 1,
          "date": "2025-05-04",
          "venue": "Updated Stadium",
          "team1": 1,
          "team2": 2,
          "winner": 1
      },
      "message": "Match updated",
      "code": "200"
  }
  ```
- **400 Bad Request**:
  ```json
  {
      "data": {
          "winner": ["Winner must be team1 or team2"]
      },
      "message": "Validation failed",
      "code": "400"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
- **404 Not Found**:
  ```json
  {
      "message": "Match not found",
      "code": "404"
  }
  ```
**Example**:
```bash
curl -X PUT /api/matches/1/ \
-H "Authorization: Bearer your_access_token" \
-H "Content-Type: application/json" \
-d '{
    "venue": "Updated Stadium",
    "winner": 1
}'
```

#### `DELETE /api/matches/{match_id}/`
**Description**: Delete a match.  
**Authentication**: JWT Bearer token.  
**Permissions**: ORGANISER.  
**Path Parameters**:
- `match_id` (integer): Match ID.
**Responses**:
- **200 OK**:
  ```json
  {
      "message": "Match deleted",
      "code": "200"
  }
  ```
- **403 Forbidden**:
  ```json
  {
      "detail": "Permission denied"
  }
  ```
- **404 Not Found**:
  ```json
  {
      "message": "Match not found",
      "code": "404"
  }
  ```
**Example**:
```bash
curl -X DELETE /api/matches/1/ \
-H "Authorization: Bearer your_access_token"
```

## Setup and Walkthrough
This section provides a step-by-step guide to set up and use the Cricket Backend API.

### Prerequisites
- **Python**: 3.8+
- **PostgreSQL**: 12+ (or SQLite for development)
- **Git**: For cloning the repository
- **Virtualenv**: For isolated Python environments

### Installation
1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd cricket_api
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Ensure `requirements.txt` includes:
   ```
   django
   djangorestframework
   djangorestframework-simplejwt
   psycopg2-binary  # For PostgreSQL
   coverage
   ```

4. **Configure Environment**:
   - Create a `.env` file or update `settings.py` with:
     ```env
     DATABASE_URL=postgres://user:password@localhost:5432/cricket_db
     SECRET_KEY=your_django_secret_key
     ```
   - Update `settings.py`:
     ```python
     INSTALLED_APPS = [
         # ...
         'rest_framework',
         'rest_framework_simplejwt',
         'api',
     ]

     REST_FRAMEWORK = {
         'DEFAULT_AUTHENTICATION_CLASSES': (
             'rest_framework_simplejwt.authentication.JWTAuthentication',
         ),
     }

     LOGGING = {
         'version': 1,
         'disable_existing_loggers': False,
         'handlers': {
             'console': {
                 'class': 'logging.StreamHandler',
             },
         },
         'loggers': {
             '': {
                 'handlers': ['console'],
                 'level': 'DEBUG',
             },
         },
     }
     ```

5. **Run Migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create Superuser**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the Server**:
   ```bash
   python manage.py runserver
   ```
   The API will be available at `http://localhost:8000/api/`.

### Basic Walkthrough
1. **Register a User**:
   ```bash
   curl -X POST http://localhost:8000/api/register/ \
   -H "Content-Type: application/json" \
   -d '{
       "username": "organiser",
       "password": "Test1234!",
       "password2": "Test1234!",
       "email": "organiser@example.com",
       "first_name": "Org",
       "last_name": "User",
       "category": "ORGANISER"
   }'
   ```

2. **Obtain JWT Token**:
   ```bash
   curl -X POST http://localhost:8000/api/token/ \
   -H "Content-Type: application/json" \
   -d '{"username": "organiser", "password": "Test1234!"}'
   ```
   Save the `access` token.

3. **Create a Team**:
   ```bash
   curl -X POST http://localhost:8000/api/teams/ \
   -H "Authorization: Bearer your_access_token" \
   -H "Content-Type: application/json" \
   -d '{
       "name": "Team A",
       "country": "India",
       "captain": 3
   }'
   ```

4. **Create a Match**:
   ```bash
   curl -X POST http://localhost:8000/api/matches/ \
   -H "Authorization: Bearer your_access_token" \
   -H "Content-Type: application/json" \
   -d '{
       "date": "2025-05-04",
       "venue": "Stadium",
       "team1": 1,
       "team2": 2,
       "winner": 1
   }'
   ```

5. **Retrieve Matches**:
   ```bash
   curl -X GET http://localhost:8000/api/matches/?page_size=5 \
   -H "Authorization: Bearer your_access_token"
   ```

## Error Handling
The API returns standard HTTP status codes with JSON error details:
- **400 Bad Request**: Invalid data or validation errors.
  ```json
  {
      "data": {
          "field_name": ["Error message"]
      },
      "message": "Validation failed",
      "code": "400"
  }
  ```
- **401 Unauthorized**: Missing or invalid JWT token.
  ```json
  {
      "detail": "Authentication credentials were not provided"
  }
  ```
- **403 Forbidden**: Insufficient permissions.
  ```json
  {
      "detail": "Permission denied"
  }
  ```
- **404 Not Found**: Resource not found.
  ```json
  {
      "message": "Resource not found",
      "code": "404"
  }
  ```

## Testing and Coverage
The API includes a comprehensive test suite (`api/tests.py`) with 92 tests covering models, serializers, and API endpoints. The test coverage is **91%**, as reported by `coverage`:
```
Name                             Stmts   Miss  Cover
----------------------------------------------------
api\__init__.py                      0      0   100%
api\admin.py                        24      0   100%
api\apps.py                          4      0   100%
api\middleware\log_requests.py      27      4    85%
api\migrations\0001_initial.py      10      0   100%
api\migrations\__init__.py           0      0   100%
api\models.py                      143      3    98%
api\permissions.py                  19      0   100%
api\serializers.py                  94      9    90%
api\tests.py                       640     45    93%
api\urls.py                          7      0   100%
api\utils.py                         3      0   100%
api\views.py                       190     48    75%
cricket_api\__init__.py              0      0   100%
cricket_api\settings.py             24      0   100%
cricket_api\urls.py                  3      0   100%
manage.py                           11      2    82%
----------------------------------------------------
TOTAL                             1199    111    91%
```

### Running Tests
```bash
coverage run manage.py test api
coverage report
```

### Test Issues
- **Anonymous User**: All API requests in tests are processed as `Anonymous`, causing unexpected successes for protected endpoints (e.g., `POST /api/matches/` returning 201). This is addressed in **Troubleshooting**.
- **Failures/Errors**: 15 test failures and 5 errors (e.g., `KeyError: 'user'`, validation issues) indicate discrepancies in response formats and model logic. These require updates to `views.py`, `serializers.py`, and `models.py`.

## Troubleshooting
### Anonymous User Issue
**Problem**: Test logs show all requests as `Anonymous`, allowing unauthorized access to protected endpoints.  
**Cause**: The `authenticate` method in `tests.py` sets the JWT token, but the test client may not process it correctly due to middleware or configuration issues.  
**Solutions**:
1. **Verify JWT Middleware**:
   Ensure `settings.py` includes:
   ```python
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': (
           'rest_framework_simplejwt.authentication.JWTAuthentication',
       ),
   }
   ```
2. **Debug Authentication**:
   Add logging to `views.py`:
   ```python
   import logging
   logger = logging.getLogger(__name__)

   class PlayerView(APIView):
       def get(self, request):
           logger.debug(f"User: {request.user}, Auth: {request.auth}")
           # ...
   ```
   Run tests with:
   ```bash
   python manage.py test api --verbosity 2
   ```
3. **Update Tests**:
   Ensure `APIClient` credentials are set correctly:
   ```python
   self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
   ```
4. **Check Middleware**:
   Ensure `AuthenticationMiddleware` is in `settings.py`:
   ```python
   MIDDLEWARE = [
       # ...
       'django.contrib.auth.middleware.AuthenticationMiddleware',
       'api.middleware.log_requests.RequestLogMiddleware',
   ]
   ```

### Common Errors
- **401 Unauthorized**: Ensure the `Authorization` header is set with a valid token.
- **403 Forbidden**: Verify the user’s `category` matches the required role.
- **400 Bad Request**: Check request body for missing or invalid fields.
- **ValidationError (Playing XI)**: Ensure no more than 11 players have `is_playing=True` for a team.

## Versioning and Change Log
### Version 1.0.0 (May 04, 2025)
- Initial release with endpoints for users, players, teams, and matches.
- JWT authentication with role-based permissions.
- 91% test coverage with 92 tests.

### Planned Updates
- Fix anonymous user issue in tests.
- Address test failures (e.g., `KeyError: 'user'`, invalid winner validation).
- Add endpoints for advanced statistics (e.g., player performance, team rankings).
- Support API versioning (e.g., `/api/v1/`).

---

**Last Updated**: May 04, 2025  
**Authors**: Cricket Backend API Development Team
