from datetime import datetime
from .extensions import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    current_balance = db.Column(db.Integer, default=100, nullable=False)
    credits_received_total = db.Column(db.Integer, default=0, nullable=False)
    monthly_sent_this_month = db.Column(db.Integer, default=0, nullable=False)
    last_credit_reset = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "current_balance": self.current_balance,
            "credits_received_total": self.credits_received_total,
            "monthly_sent_this_month": self.monthly_sent_this_month,
        }


class Recognition(db.Model):
    __tablename__ = "recognitions"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship("Student", foreign_keys=[sender_id], backref="sent_recognitions")
    receiver = db.relationship("Student", foreign_keys=[receiver_id], backref="received_recognitions")

    def to_dict(self):
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "credits": self.credits,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Endorsement(db.Model):
    __tablename__ = "endorsements"

    id = db.Column(db.Integer, primary_key=True)
    recognition_id = db.Column(db.Integer, db.ForeignKey("recognitions.id"), nullable=False)
    endorser_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    recognition = db.relationship("Recognition", backref="endorsements")
    endorser = db.relationship("Student", backref="endorsements")

    __table_args__ = (
        db.UniqueConstraint("recognition_id", "endorser_id", name="unique_recognition_endorser"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "recognition_id": self.recognition_id,
            "endorser_id": self.endorser_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Redemption(db.Model):
    __tablename__ = "redemptions"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    credits_redeemed = db.Column(db.Integer, nullable=False)
    voucher_value_inr = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("Student", backref="redemptions")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "credits_redeemed": self.credits_redeemed,
            "voucher_value_inr": self.voucher_value_inr,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MonthlyResetLog(db.Model):
    __tablename__ = "monthly_reset_logs"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    carried_forward = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("Student", backref="reset_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "month": self.month,
            "year": self.year,
            "carried_forward": self.carried_forward,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

