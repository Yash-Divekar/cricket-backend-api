# Cricket Backend API

A RESTful API for managing cricket-related data, including users, teams, players, and matches. Built with **Django REST Framework** and **SQLite**, it supports role-based authentication (ADMIN, ORGANISER, CAPTAIN, PLAYER) using JWT.

## Features
- User registration and JWT authentication.
- CRUD operations for teams, players, and matches.
- Role-based permissions for secure access.
- SQLite database for lightweight development.

## Installation

### Prerequisites
- Python 3.8+
- Git
- Virtualenv (recommended)

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/<your-username>/cricket-backend-api.git
   cd cricket-backend-api
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Migrations**:
   The project uses SQLite (`db.sqlite3`). Run:
   ```bash
   python manage.py migrate
   ```

5. **Create Superuser** (optional):
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the Server**:
   ```bash
   python manage.py runserver
   ```
   Access the API at `http://localhost:8000/api/`.

## Usage

### Register a User
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

### Obtain JWT Token
```bash
curl -X POST http://localhost:8000/api/token/ \
-H "Content-Type: application/json" \
-d '{"username": "organiser", "password": "Test1234!"}'
```

### Create a Team
```bash
curl -X POST http://localhost:8000/api/teams/ \
-H "Authorization: Bearer <your_access_token>" \
-H "Content-Type: application/json" \
-d '{
    "name": "Team A",
    "country": "India",
    "captain": 3
}'
```

See the [full documentation](docs/api_documentation.md) for all endpoints.

## Running Tests
The project includes 92 tests with 91% coverage.
```bash
coverage run manage.py test api
coverage report
```

**Note**: Tests currently show requests as `Anonymous`. Contributors are needed to fix JWT authentication in tests (see [Troubleshooting](#troubleshooting)).

## Troubleshooting
- **Anonymous User Issue**: Tests bypass authentication, allowing unauthorized access. Check `settings.py` for `rest_framework_simplejwt` configuration and ensure `Authorization` headers are set in test clients.
- **Database Issues**: Ensure `db.sqlite3` is writable and migrations are applied.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) and report issues via GitHub.

## License
[MIT License](LICENSE)

---

**Contact**: [your-email@example.com](mailto:your-email@example.com)  
**Issues**: [GitHub Issues](https://github.com/<your-username>/cricket-backend-api/issues)