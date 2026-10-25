# Flask Authentication and Notes API

A Flask backend that provides session-based authentication and user-owned notes management. It uses SQLAlchemy for database operations, Flask-Migrate for database migrations, and Flask-Bcrypt for password hashing.

## Features

- User registration with password confirmation.
- Login and logout using Flask sessions.
- Secure password hashing.
- Session status checking.
- Create, read, update, and delete notes.
- Authorization to ensure users can access only their own notes.
- Paginated notes listing.
- SQLite database and migration support.
- Automated tests using pytest.

## Technology Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Bcrypt
- pytest
- SQLite

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/calebblessings-rgb/flask-c10-summative-lab-sessions-and-jwt-clients.git
cd flask-c10-summative-lab-sessions-and-jwt-clients