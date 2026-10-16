from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import re

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request, session, send_from_directory
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from backend.config import Config
from backend.services.matching import rank_internships
from backend.services import sqlite_reporting


VALID_ROLES = {"student", "company", "admin"}
VALID_STATUSES = {"pending", "shortlisted", "rejected", "accepted"}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value, max_length=200):
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def valid_email(value):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value or ""))


def serialize(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items() if key != "password_hash"}
    if isinstance(value, list):
        return [serialize(item) for item in value]
    return value


def object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def create_app(test_config=None):
    app = Flask(__name__, static_folder="../frontend", static_url_path="/static")
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    client = None
    db = None
    if app.config.get("MONGO_CLIENT") is not None:
        client = app.config["MONGO_CLIENT"]
        db = client[app.config["MONGO_DB_NAME"]]
    elif app.config.get("TESTING"):
        # Unit tests can exercise routes without a live database.
        db = None
    else:
        client = MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=2500)
        db = client[app.config["MONGO_DB_NAME"]]

    app.extensions["mongo_client"] = client
    app.extensions["mongo_db"] = db
    sql_path = app.config["SQLITE_PATH"]
    sqlite_reporting.initialize(sql_path)

    if db is not None:
        try:
            db.users.create_index([("email", ASCENDING)], unique=True)
            db.applications.create_index(
                [("student_id", ASCENDING), ("internship_id", ASCENDING)], unique=True
            )
            db.internships.create_index([("created_at", DESCENDING)])
            db.internships.create_index([("required_skills", ASCENDING)])
        except PyMongoError:
            app.logger.exception("Could not create MongoDB indexes")

    def database_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if app.extensions["mongo_db"] is None:
                return jsonify({"error": "Database is not configured for this test context."}), 503
            return fn(*args, **kwargs)
        return wrapper

    def current_user():
        user_id = session.get("user_id")
        if not user_id or db is None:
            return None
        oid = object_id(user_id)
        if oid is None:
            return None
        return db.users.find_one({"_id": oid})

    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if current_user() is None:
                return jsonify({"error": "Please log in first."}), 401
            return fn(*args, **kwargs)
        return wrapper

    def role_required(*roles):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                user = current_user()
                if user is None:
                    return jsonify({"error": "Please log in first."}), 401
                if user.get("role") not in roles:
                    return jsonify({"error": "You do not have permission for this action."}), 403
                return fn(*args, **kwargs)
            return wrapper
        return decorator

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/health")
    def health():
        db_status = "not_configured"
        if db is not None:
            try:
                db.command("ping")
                db_status = "connected"
            except PyMongoError:
                db_status = "disconnected"
        return jsonify({"status": "ok", "mongodb": db_status})

    @app.post("/api/auth/register")
    @database_required
    def register():
        data = request.get_json(silent=True) or {}
        name = clean_text(data.get("name"), 100)
        email = clean_text(data.get("email"), 254).lower()
        password = data.get("password", "")
        role = clean_text(data.get("role"), 20).lower()
        if len(name) < 2:
            return jsonify({"error": "Name must contain at least 2 characters."}), 400
        if not valid_email(email):
            return jsonify({"error": "Enter a valid email address."}), 400
        if not isinstance(password, str) or len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters."}), 400
        if role not in {"student", "company", "admin"}:
            return jsonify({"error": "Choose a valid role."}), 400
        if role == "admin" and not app.config["ALLOW_ADMIN_REGISTRATION"]:
            return jsonify({"error": "Admin self-registration is disabled."}), 403
        user = {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "role": role,
            "created_at": utc_now(),
        }
        try:
            result = db.users.insert_one(user)
        except DuplicateKeyError:
            return jsonify({"error": "An account with this email already exists."}), 409
        user["_id"] = result.inserted_id
        session.clear()
        session["user_id"] = str(result.inserted_id)
        return jsonify({"user": serialize(user)}), 201

    @app.post("/api/auth/login")
    @database_required
    def login():
        data = request.get_json(silent=True) or {}
        email = clean_text(data.get("email"), 254).lower()
        password = data.get("password", "")
        user = db.users.find_one({"email": email})
        if not user or not isinstance(password, str) or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid email or password."}), 401
        session.clear()
        session["user_id"] = str(user["_id"])
        return jsonify({"user": serialize(user)})

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify({"message": "Logged out."})

    @app.get("/api/me")
    @login_required
    def me():
        return jsonify({"user": serialize(current_user())})

    @app.get("/api/student/profile")
    @login_required
    @role_required("student")
    def get_student_profile():
        profile = db.student_profiles.find_one({"user_id": session["user_id"]}) or {
            "user_id": session["user_id"], "skills": [], "interests": "", "education": "", "resume_url": ""
        }
        return jsonify({"profile": serialize(profile)})

    @app.put("/api/student/profile")
    @login_required
    @role_required("student")
    def update_student_profile():
        data = request.get_json(silent=True) or {}
        raw_skills = data.get("skills", [])
        if not isinstance(raw_skills, list) or any(not isinstance(s, str) for s in raw_skills):
            return jsonify({"error": "Skills must be a list of text values."}), 400
        skills = sorted({s.strip()[:60] for s in raw_skills if s.strip()})[:50]
        profile = {
            "user_id": session["user_id"],
            "skills": skills,
            "interests": clean_text(data.get("interests"), 1000),
            "education": clean_text(data.get("education"), 200),
            "resume_url": clean_text(data.get("resume_url"), 500),
            "updated_at": utc_now(),
        }
        db.student_profiles.update_one({"user_id": session["user_id"]}, {"$set": profile}, upsert=True)
        return jsonify({"profile": profile})

    @app.route("/api/internships", methods=["GET", "POST"])
    @database_required
    def internships():
        if request.method == "GET":
            query = {"active": {"$ne": False}}
            search = clean_text(request.args.get("q"), 100)
            if search:
                query["$or"] = [
                    {"title": {"$regex": re.escape(search), "$options": "i"}},
                    {"company_name": {"$regex": re.escape(search), "$options": "i"}},
                    {"location": {"$regex": re.escape(search), "$options": "i"}},
                ]
            items = list(db.internships.find(query).sort("created_at", DESCENDING).limit(100))
            return jsonify({"internships": [serialize(item) for item in items]})

        user = current_user()
        if user is None:
            return jsonify({"error": "Please log in first."}), 401
        if user.get("role") not in {"company", "admin"}:
            return jsonify({"error": "Only companies can post internships."}), 403
        data = request.get_json(silent=True) or {}
        title = clean_text(data.get("title"), 120)
        description = clean_text(data.get("description"), 3000)
        raw_skills = data.get("required_skills", [])
        if len(title) < 3 or len(description) < 10:
            return jsonify({"error": "Add a title and a description of at least 10 characters."}), 400
        if not isinstance(raw_skills, list) or any(not isinstance(s, str) for s in raw_skills):
            return jsonify({"error": "Required skills must be a list."}), 400
        skills = sorted({s.strip()[:60] for s in raw_skills if s.strip()})[:50]
        item = {
            "title": title,
            "description": description,
            "required_skills": skills,
            "location": clean_text(data.get("location"), 120) or "Not specified",
            "company_id": str(user["_id"]),
            "company_name": user["name"],
            "active": True,
            "created_at": utc_now(),
        }
        result = db.internships.insert_one(item)
        item["_id"] = result.inserted_id
        sqlite_reporting.upsert_internship(sql_path, str(result.inserted_id), title, user["name"])
        return jsonify({"internship": serialize(item)}), 201

    @app.put("/api/internships/<internship_id>")
    @login_required
    @role_required("company", "admin")
    def update_internship(internship_id):
        oid = object_id(internship_id)
        if oid is None:
            return jsonify({"error": "Invalid internship ID."}), 400
        item = db.internships.find_one({"_id": oid})
        if not item:
            return jsonify({"error": "Internship not found."}), 404
        user = current_user()
        if user["role"] != "admin" and item.get("company_id") != str(user["_id"]):
            return jsonify({"error": "You can only edit your own listings."}), 403
        data = request.get_json(silent=True) or {}
        updates = {}
        for field, max_len in (("title", 120), ("description", 3000), ("location", 120)):
            if field in data:
                updates[field] = clean_text(data[field], max_len)
        if "required_skills" in data:
            if not isinstance(data["required_skills"], list) or any(not isinstance(s, str) for s in data["required_skills"]):
                return jsonify({"error": "Required skills must be a list."}), 400
            updates["required_skills"] = sorted({s.strip()[:60] for s in data["required_skills"] if s.strip()})[:50]
        if "active" in data:
            updates["active"] = bool(data["active"])
        if updates:
            db.internships.update_one({"_id": oid}, {"$set": updates})
            item.update(updates)
        return jsonify({"internship": serialize(item)})

    @app.delete("/api/internships/<internship_id>")
    @login_required
    @role_required("company", "admin")
    def delete_internship(internship_id):
        oid = object_id(internship_id)
        if oid is None:
            return jsonify({"error": "Invalid internship ID."}), 400
        item = db.internships.find_one({"_id": oid})
        if not item:
            return jsonify({"error": "Internship not found."}), 404
        user = current_user()
        if user["role"] != "admin" and item.get("company_id") != str(user["_id"]):
            return jsonify({"error": "You can only remove your own listings."}), 403
        db.internships.update_one({"_id": oid}, {"$set": {"active": False}})
        return jsonify({"message": "Internship closed."})

    @app.post("/api/internships/<internship_id>/apply")
    @login_required
    @role_required("student")
    def apply(internship_id):
        oid = object_id(internship_id)
        if oid is None:
            return jsonify({"error": "Invalid internship ID."}), 400
        internship = db.internships.find_one({"_id": oid, "active": {"$ne": False}})
        if not internship:
            return jsonify({"error": "Internship not found or closed."}), 404
        student_id = session["user_id"]
        profile = db.student_profiles.find_one({"user_id": student_id}) or {}
        application = {
            "student_id": student_id,
            "student_name": current_user()["name"],
            "internship_id": str(oid),
            "internship_title": internship["title"],
            "company_id": internship.get("company_id"),
            "company_name": internship.get("company_name", ""),
            "status": "pending",
            "applied_at": utc_now(),
            "skills_at_application": profile.get("skills", []),
        }
        try:
            result = db.applications.insert_one(application)
        except DuplicateKeyError:
            return jsonify({"error": "You have already applied to this internship."}), 409
        application["_id"] = result.inserted_id
        sqlite_reporting.upsert_user(sql_path, student_id, current_user()["name"], "student")
        sqlite_reporting.upsert_application(sql_path, str(result.inserted_id), student_id, str(oid), "pending")
        return jsonify({"application": serialize(application)}), 201

    @app.get("/api/applications/mine")
    @login_required
    @role_required("student")
    def my_applications():
        items = list(db.applications.find({"student_id": session["user_id"]}).sort("applied_at", DESCENDING))
        return jsonify({"applications": [serialize(item) for item in items]})

    @app.get("/api/company/applications")
    @login_required
    @role_required("company", "admin")
    def company_applications():
        user = current_user()
        query = {} if user["role"] == "admin" else {"company_id": str(user["_id"])}
        items = list(db.applications.find(query).sort("applied_at", DESCENDING).limit(500))
        return jsonify({"applications": [serialize(item) for item in items]})

    @app.patch("/api/applications/<application_id>/status")
    @login_required
    @role_required("company", "admin")
    def update_application_status(application_id):
        oid = object_id(application_id)
        if oid is None:
            return jsonify({"error": "Invalid application ID."}), 400
        data = request.get_json(silent=True) or {}
        status = clean_text(data.get("status"), 20).lower()
        if status not in VALID_STATUSES:
            return jsonify({"error": "Status must be pending, shortlisted, rejected, or accepted."}), 400
        application = db.applications.find_one({"_id": oid})
        if not application:
            return jsonify({"error": "Application not found."}), 404
        user = current_user()
        if user["role"] != "admin" and application.get("company_id") != str(user["_id"]):
            return jsonify({"error": "You can only update applications to your internships."}), 403
        db.applications.update_one({"_id": oid}, {"$set": {"status": status, "updated_at": utc_now()}})
        sqlite_reporting.upsert_application(
            sql_path, str(oid), application["student_id"], application["internship_id"], status
        )
        return jsonify({"message": "Application status updated.", "status": status})

    @app.get("/api/recommendations")
    @login_required
    @role_required("student")
    def recommendations():
        profile = db.student_profiles.find_one({"user_id": session["user_id"]}) or {}
        already_applied = {item["internship_id"] for item in db.applications.find(
            {"student_id": session["user_id"]}, {"internship_id": 1}
        )}
        internships_list = [
            item for item in db.internships.find({"active": {"$ne": False}})
            if str(item["_id"]) not in already_applied
        ]
        ranked = rank_internships(profile.get("skills", []), [serialize(item) for item in internships_list])
        return jsonify({"recommendations": ranked[:50]})

    @app.get("/api/analytics")
    @login_required
    @role_required("admin", "company")
    def analytics():
        user = current_user()
        internship_query = {} if user["role"] == "admin" else {"company_id": str(user["_id"])}
        internship_ids = [str(item["_id"]) for item in db.internships.find(internship_query, {"_id": 1})]
        app_query = {} if user["role"] == "admin" else {"company_id": str(user["_id"])}
        status_counts = list(db.applications.aggregate([
            {"$match": app_query},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]))
        skill_counts = list(db.student_profiles.aggregate([
            {"$unwind": "$skills"},
            {"$group": {"_id": {"$toLower": "$skills"}, "students": {"$sum": 1}}},
            {"$sort": {"students": -1}},
            {"$limit": 10},
        ]))
        return jsonify({
            "internship_count": len(internship_ids),
            "application_statuses": [{"status": item["_id"], "count": item["count"]} for item in status_counts],
            "popular_student_skills": [{"skill": item["_id"], "students": item["students"]} for item in skill_counts],
            "sql_application_summary": sqlite_reporting.application_summary(sql_path),
        })

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Endpoint not found."}), 404
        return "Page not found", 404

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("Unexpected server error")
        return jsonify({"error": "An unexpected server error occurred."}), 500

    return app
