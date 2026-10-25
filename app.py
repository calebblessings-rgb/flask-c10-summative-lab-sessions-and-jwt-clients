import os

from flask import Flask, jsonify, request, session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from extensions import db, migrate, bcrypt
from models import User, Note


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "dev-only-change-this-secret"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "sqlite:///app.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    @app.get("/")
    def index():
        return jsonify({"message": "Flask backend is running"})

    @app.post("/signup")
    def signup():
        data = request.get_json(silent=True) or {}

        username = data.get("username", "").strip()
        password = data.get("password", "")
        confirmation = data.get("password_confirmation", "")

        if not username or not password:
            return jsonify({"error": "Username and password are required."}), 400

        if password != confirmation:
            return jsonify({"error": "Passwords do not match."}), 400

        if len(password.encode("utf-8")) > 72:
            return jsonify({"error": "Password must not exceed 72 bytes."}), 400

        user = User(
            username=username,
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8")
        )

        db.session.add(user)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "Username already exists."}), 409

        session.clear()
        session["user_id"] = user.id

        return jsonify(user.to_dict()), 201

    @app.post("/login")
    def login():
        data = request.get_json(silent=True) or {}

        username = data.get("username", "").strip()
        password = data.get("password", "")

        user = db.session.scalar(
            select(User).where(User.username == username)
        )

        if user is None or not bcrypt.check_password_hash(
            user.password_hash, password
        ):
            return jsonify({"error": "Invalid username or password."}), 401

        session.clear()
        session["user_id"] = user.id

        return jsonify(user.to_dict()), 200

    @app.get("/check_session")
    def check_session():
        user_id = session.get("user_id")

        if user_id is None:
            return jsonify({}), 200

        user = db.session.get(User, user_id)

        if user is None:
            session.clear()
            return jsonify({}), 200

        return jsonify(user.to_dict()), 200

    @app.delete("/logout")
    def logout():
        session.clear()
        return jsonify({}), 200

    @app.get("/notes")
    def get_notes():
        user_id = session.get("user_id")

        if user_id is None:
            return jsonify({"error": "Authentication required."}), 401

        try:
            page = max(1, int(request.args.get("page", 1)))
            per_page = min(100, max(1, int(request.args.get("per_page", 10))))
        except ValueError:
            return jsonify({"error": "Page values must be integers."}), 400

        pagination = db.paginate(
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(Note.id),
            page=page,
            per_page=per_page,
            error_out=False
        )

        return jsonify({
            "notes": [note.to_dict() for note in pagination.items],
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages
        }), 200

    @app.post("/notes")
    def create_note():
        user_id = session.get("user_id")

        if user_id is None:
            return jsonify({"error": "Authentication required."}), 401

        data = request.get_json(silent=True) or {}
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()

        if not title or not content:
            return jsonify({"error": "Title and content are required."}), 400

        note = Note(
            title=title,
            content=content,
            user_id=user_id
        )

        db.session.add(note)
        db.session.commit()

        return jsonify(note.to_dict()), 201

    @app.route("/notes/<int:note_id>", methods=["GET", "PATCH", "DELETE"])
    def note_detail(note_id):
        user_id = session.get("user_id")

        if user_id is None:
            return jsonify({"error": "Authentication required."}), 401

        note = db.session.scalar(
            select(Note).where(
                Note.id == note_id,
                Note.user_id == user_id
            )
        )

        if note is None:
            return jsonify({"error": "Note not found."}), 404

        if request.method == "GET":
            return jsonify(note.to_dict()), 200

        if request.method == "PATCH":
            data = request.get_json(silent=True) or {}

            if "title" in data:
                if not isinstance(data["title"], str) or not data["title"].strip():
                    return jsonify({"error": "Title cannot be empty."}), 400
                note.title = data["title"].strip()

            if "content" in data:
                if not isinstance(data["content"], str) or not data["content"].strip():
                    return jsonify({"error": "Content cannot be empty."}), 400
                note.content = data["content"].strip()

            db.session.commit()
            return jsonify(note.to_dict()), 200

        db.session.delete(note)
        db.session.commit()
        return jsonify({}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=5555, debug=True)
