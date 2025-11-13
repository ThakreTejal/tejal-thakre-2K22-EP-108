from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .config import Config
from .extensions import db, migrate
from .models import Student
from .services import create_recognition, endorse, redeem, leaderboard, run_monthly_reset_for_all_students

# Module-level scheduler instance
_scheduler = None


def create_app(config_class=Config):
    global _scheduler
    
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize scheduler (only once)
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()
        
        # Schedule monthly reset job (runs on 1st of each month at 00:05)
        _scheduler.add_job(
            func=run_monthly_reset_for_all_students,
            trigger=CronTrigger(day=1, hour=0, minute=5),
            id='monthly_credit_reset',
            name='Monthly Credit Reset',
            replace_existing=True,
        )

    @app.route("/students", methods=["POST"])
    def create_student():
        """Create a new student with default balance of 100."""
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        if "name" not in data:
            return jsonify({"error": "name is required"}), 400

        if not isinstance(data["name"], str) or not data["name"].strip():
            return jsonify({"error": "name must be a non-empty string"}), 400

        student = Student(name=data["name"].strip())
        db.session.add(student)
        db.session.commit()

        return jsonify(student.to_dict()), 201

    @app.route("/students/<int:student_id>", methods=["GET"])
    def get_student(student_id):
        """Get student information by ID."""
        student = Student.query.get(student_id)

        if not student:
            return jsonify({"error": "Student not found"}), 404

        return jsonify(student.to_dict()), 200

    @app.route("/recognitions", methods=["POST"])
    def create_recognition_endpoint():
        """Create a recognition transaction between students."""
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        # Validate required fields
        required_fields = ["sender_id", "receiver_id", "credits"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        # Validate credits is positive
        try:
            credits = int(data["credits"])
            if credits <= 0:
                return jsonify({"error": "credits must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "credits must be a valid integer"}), 400

        try:
            recognition = create_recognition(
                sender_id=data["sender_id"],
                receiver_id=data["receiver_id"],
                credits=credits,
                message=data.get("message"),
            )
            return jsonify(recognition.to_dict()), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/recognitions/<int:recognition_id>/endorse", methods=["POST"])
    def endorse_recognition(recognition_id):
        """Endorse a recognition."""
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        if "endorser_id" not in data:
            return jsonify({"error": "endorser_id is required"}), 400

        try:
            endorsement = endorse(
                recognition_id=recognition_id,
                endorser_id=data["endorser_id"],
            )
            return jsonify(endorsement.to_dict()), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/students/<int:student_id>/redeem", methods=["POST"])
    def redeem_credits(student_id):
        """Redeem credits for a student."""
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        if "credits" not in data:
            return jsonify({"error": "credits is required"}), 400

        # Validate credits is a positive integer
        try:
            credits = int(data["credits"])
            if credits <= 0:
                return jsonify({"error": "credits must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "credits must be a valid integer"}), 400

        try:
            redemption = redeem(
                student_id=student_id,
                credits_to_redeem=credits,
            )
            return jsonify(redemption.to_dict()), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/leaderboard", methods=["GET"])
    def get_leaderboard():
        """Get the top students ranked by credits received."""
        try:
            limit = int(request.args.get("limit", 10))
            if limit <= 0:
                return jsonify({"error": "limit must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "limit must be a valid integer"}), 400

        leaderboard_data = leaderboard(limit=limit)
        return jsonify(leaderboard_data), 200

    @app.route("/admin/run-monthly-reset", methods=["GET"])
    def run_monthly_reset():
        """Manually trigger monthly reset for all students (for testing)."""
        try:
            reset_count = run_monthly_reset_for_all_students()
            return jsonify({
                "message": "Monthly reset completed successfully",
                "students_reset": reset_count
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({"status": "ok"}), 200

    return app

