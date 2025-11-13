from datetime import datetime
from sqlalchemy import func
from .extensions import db
from .models import Student, Recognition, Endorsement, Redemption, MonthlyResetLog


def create_recognition(sender_id, receiver_id, credits, message=None):
    """
    Create a recognition transaction between two students.
    
    Business rules:
    - A student cannot send credits to themselves
    - A student cannot send more credits than they currently have
    - A student cannot send more than 100 credits in a month
    
    Raises ValueError if any rule is violated.
    """
    # Validate sender and receiver exist
    sender = Student.query.get(sender_id)
    if not sender:
        raise ValueError(f"Student with id {sender_id} not found")

    receiver = Student.query.get(receiver_id)
    if not receiver:
        raise ValueError(f"Student with id {receiver_id} not found")

    # Rule 1: Cannot send to self
    if sender_id == receiver_id:
        raise ValueError("A student cannot send credits to themselves")

    # Rule 2: Cannot send more than current balance
    if credits > sender.current_balance:
        raise ValueError(
            f"Insufficient balance. Current balance: {sender.current_balance}, "
            f"attempted to send: {credits}"
        )

    # Rule 3: Cannot send more than 100 credits per month
    if sender.monthly_sent_this_month + credits > 100:
        raise ValueError(
            f"Monthly limit exceeded. Already sent this month: {sender.monthly_sent_this_month}, "
            f"attempted to send: {credits}. Maximum allowed per month: 100"
        )

    # All validations passed - perform the transaction
    # Deduct credits from sender
    sender.current_balance -= credits
    sender.monthly_sent_this_month += credits

    # Add credits to receiver
    receiver.current_balance += credits
    receiver.credits_received_total += credits

    # Create recognition record
    recognition = Recognition(
        sender_id=sender_id,
        receiver_id=receiver_id,
        credits=credits,
        message=message,
        created_at=datetime.utcnow(),
    )

    db.session.add(recognition)
    db.session.commit()

    return recognition


def endorse(recognition_id, endorser_id):
    """
    Create an endorsement for a recognition.
    
    Business rules:
    - A student can endorse a recognition only once
    - Endorsements do NOT affect credits or balances
    
    Raises ValueError if any rule is violated.
    """
    # Validate recognition exists
    recognition = Recognition.query.get(recognition_id)
    if not recognition:
        raise ValueError(f"Recognition with id {recognition_id} not found")

    # Validate endorser exists
    endorser = Student.query.get(endorser_id)
    if not endorser:
        raise ValueError(f"Endorser with id {endorser_id} not found")

    # Check if endorsement already exists (unique constraint check)
    existing_endorsement = Endorsement.query.filter_by(
        recognition_id=recognition_id,
        endorser_id=endorser_id
    ).first()

    if existing_endorsement:
        raise ValueError("This student has already endorsed this recognition")

    # Create endorsement
    endorsement = Endorsement(
        recognition_id=recognition_id,
        endorser_id=endorser_id,
        created_at=datetime.utcnow(),
    )

    db.session.add(endorsement)
    db.session.commit()

    return endorsement


def redeem(student_id, credits_to_redeem):
    """
    Redeem credits for a student, converting them into vouchers.
    
    Business rules:
    - Students can redeem only the credits they currently have
    - credits_to_redeem must be > 0
    - Redemption permanently deducts credits from current_balance
    - Voucher value = credits_redeemed * 5 (₹5 per credit)
    
    Raises ValueError if any rule is violated.
    """
    # Validate student exists
    student = Student.query.get(student_id)
    if not student:
        raise ValueError(f"Student with id {student_id} not found")

    # Validate credits_to_redeem > 0
    if credits_to_redeem <= 0:
        raise ValueError("credits_to_redeem must be greater than 0")

    # Check student has sufficient balance
    if student.current_balance < credits_to_redeem:
        raise ValueError(
            f"Insufficient credits. Current balance: {student.current_balance}, "
            f"attempted to redeem: {credits_to_redeem}"
        )

    # Calculate voucher value (₹5 per credit)
    voucher_value_inr = credits_to_redeem * 5

    # Deduct credits from student's balance
    student.current_balance -= credits_to_redeem

    # Create redemption record
    redemption = Redemption(
        student_id=student_id,
        credits_redeemed=credits_to_redeem,
        voucher_value_inr=voucher_value_inr,
        created_at=datetime.utcnow(),
    )

    db.session.add(redemption)
    db.session.commit()

    return redemption


def leaderboard(limit=10):
    """
    Get the top students ranked by credits received.
    
    Ranking rules:
    - Sort by credits_received_total in descending order
    - If two students have equal credits_received_total, sort by student ID ascending
    
    Returns a list of dicts with:
    - student_id
    - name
    - credits_received_total
    - recognition_count (number of recognitions received)
    - endorsement_count (total endorsements across all their received recognitions)
    """
    # Query students with counts for recognitions and endorsements
    # Using outer joins to include students with 0 recognitions/endorsements
    results = db.session.query(
        Student.id,
        Student.name,
        Student.credits_received_total,
        func.count(Recognition.id.distinct()).label('recognition_count'),
        func.count(Endorsement.id.distinct()).label('endorsement_count')
    ).outerjoin(
        Recognition, Recognition.receiver_id == Student.id
    ).outerjoin(
        Endorsement, Endorsement.recognition_id == Recognition.id
    ).group_by(
        Student.id, Student.name, Student.credits_received_total
    ).order_by(
        Student.credits_received_total.desc(),
        Student.id.asc()
    ).limit(limit).all()
    
    # Convert to list of dicts
    leaderboard_data = []
    for result in results:
        leaderboard_data.append({
            "student_id": result.id,
            "name": result.name,
            "credits_received_total": result.credits_received_total,
            "recognition_count": result.recognition_count or 0,
            "endorsement_count": result.endorsement_count or 0,
        })
    
    return leaderboard_data


def ensure_monthly_reset(student):
    """
    Ensure a student's credits are reset for the current month if needed.
    
    Reset rules:
    - Students get a base allowance of 100 credits
    - Up to 50 unused credits from previous month may be carried forward
    - monthly_sent_this_month resets to 0
    - last_credit_reset is updated to current month
    - A MonthlyResetLog entry is created
    
    Returns True if reset was performed, False if not needed.
    """
    now = datetime.utcnow()
    current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Check if reset is needed
    if student.last_credit_reset is None:
        # First time reset
        needs_reset = True
    else:
        # Check if last reset was before current month
        last_reset_month = student.last_credit_reset.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        needs_reset = last_reset_month < current_month
    
    if not needs_reset:
        return False
    
    # Compute carry-forward (max 50 credits)
    carry_forward = min(50, student.current_balance)
    
    # Set new balance
    student.current_balance = 100 + carry_forward
    
    # Reset monthly sent counter
    student.monthly_sent_this_month = 0
    
    # Update last reset timestamp
    student.last_credit_reset = now
    
    # Create reset log entry
    reset_log = MonthlyResetLog(
        student_id=student.id,
        month=now.month,
        year=now.year,
        carried_forward=carry_forward,
        created_at=now,
    )
    
    db.session.add(reset_log)
    db.session.commit()
    
    return True


def run_monthly_reset_for_all_students():
    """
    Run monthly reset for all students who need it.
    This function is called by the scheduler or manually via admin endpoint.
    """
    students = Student.query.all()
    reset_count = 0
    
    for student in students:
        if ensure_monthly_reset(student):
            reset_count += 1
    
    return reset_count

