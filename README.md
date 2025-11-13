# Boostly

Boostly is a Flask-based application that enables students to recognize and reward each other with credits. The first feature allows students to create accounts and send credits to their peers, with built-in validation to ensure fair and controlled credit distribution.

## Tech Stack

- **Flask** - Web framework
- **SQLAlchemy** - ORM for database operations
- **SQLite** - Database
- **Flask-Migrate** - Database migrations

## Setup Instructions

### 1. Create Virtual Environment

**Unix/Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Run Migrations

**Unix/Mac/Linux:**
```bash
export FLASK_APP=run.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

**Windows:**
```powershell
$env:FLASK_APP="run.py"
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. Start the Server

From the project root directory:

```bash
python run.py
```

The server will start on `http://localhost:5000`.

## API Documentation

### POST /students

Create a new student account. Each student starts with a default balance of 100 credits.

**Request:**
```json
{
  "name": "Alice"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "name": "Alice",
  "current_balance": 100,
  "credits_received_total": 0,
  "monthly_sent_this_month": 0
}
```

**Error Responses:**
- `400 Bad Request` - If name is missing from request body

---

### GET /students/<id>

Retrieve information about a specific student by their ID.

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "Alice",
  "current_balance": 90,
  "credits_received_total": 0,
  "monthly_sent_this_month": 10
}
```

**Error Responses:**
- `404 Not Found` - If student with the given ID doesn't exist

---

### POST /recognitions

Send credits from one student to another. This endpoint enforces several business rules to ensure valid transactions.

**Request:**
```json
{
  "sender_id": 1,
  "receiver_id": 2,
  "credits": 10,
  "message": "Thanks for your help!"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "sender_id": 1,
  "receiver_id": 2,
  "credits": 10,
  "message": "Thanks for your help!",
  "created_at": "2024-01-15T10:30:00.000000"
}
```

**Error Responses:**
- `400 Bad Request` - If required fields (sender_id, receiver_id, credits) are missing
- `400 Bad Request` - If sender tries to send credits to themselves: `"A student cannot send credits to themselves"`
- `400 Bad Request` - If sender has insufficient balance: `"Insufficient balance. Current balance: 50, attempted to send: 100"`
- `400 Bad Request` - If sender exceeds monthly limit: `"Monthly limit exceeded. Already sent this month: 95, attempted to send: 10. Maximum allowed per month: 100"`
- `400 Bad Request` - If sender or receiver ID doesn't exist

**Business Rules:**
- A student cannot send credits to themselves
- A student cannot send more credits than their current balance
- A student cannot send more than 100 credits total in a month
- On successful recognition:
  - Credits are deducted from sender's `current_balance`
  - Sender's `monthly_sent_this_month` is incremented
  - Credits are added to receiver's `current_balance`
  - Receiver's `credits_received_total` is incremented
  - A recognition record is created

## Quick Testing Guide

Here are three curl commands to quickly test the application:

**1. Create student Alice:**
```bash
curl -X POST http://localhost:5000/students \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice"}'
```

Expected: Alice is created with ID 1, starting balance of 100 credits.

**2. Create student Bob:**
```bash
curl -X POST http://localhost:5000/students \
  -H "Content-Type: application/json" \
  -d '{"name": "Bob"}'
```

Expected: Bob is created with ID 2, starting balance of 100 credits.

**3. Alice sends 10 credits to Bob:**
```bash
curl -X POST http://localhost:5000/recognitions \
  -H "Content-Type: application/json" \
  -d '{"sender_id": 1, "receiver_id": 2, "credits": 10, "message": "Thanks for your help!"}'
```

Expected outcomes:
- Alice's `current_balance` decreases from 100 to 90
- Alice's `monthly_sent_this_month` increases from 0 to 10
- Bob's `current_balance` increases from 100 to 110
- Bob's `credits_received_total` increases from 0 to 10
- A recognition record is created with the transaction details

You can verify the balance changes by calling `GET /students/1` and `GET /students/2`.

## Endorsements

Students can endorse recognitions to show their support. Endorsements are a way for students to acknowledge and appreciate the recognition that others have given, without affecting credit balances.

**Business Rule:** A student can endorse a recognition only once. Attempting to endorse the same recognition twice will result in an error.

### POST /recognitions/<id>/endorse

Endorse a recognition by providing the endorser's student ID.

**Request:**
```json
{
  "endorser_id": 3
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "recognition_id": 1,
  "endorser_id": 3,
  "created_at": "2024-01-15T11:00:00.000000"
}
```

**Error Responses:**
- `400 Bad Request` - If `endorser_id` is missing from request body
- `400 Bad Request` - If recognition with the given ID doesn't exist: `"Recognition with id {id} not found"`
- `400 Bad Request` - If endorser with the given ID doesn't exist: `"Endorser with id {id} not found"`
- `400 Bad Request` - If student has already endorsed this recognition: `"This student has already endorsed this recognition"`

**Note:** Endorsements do not affect credit balances or any student statistics. They are purely for showing support and appreciation.

### Endorsements Usage Example

**1. Create student Charlie:**
```bash
curl -X POST http://localhost:5000/students \
  -H "Content-Type: application/json" \
  -d '{"name": "Charlie"}'
```

**2. Charlie endorses recognition #1:**
```bash
curl -X POST http://localhost:5000/recognitions/1/endorse \
  -H "Content-Type: application/json" \
  -d '{"endorser_id": 3}'
```

Expected: Endorsement is created successfully, returning the endorsement details.

**3. Charlie tries to endorse the same recognition again (should fail):**
```bash
curl -X POST http://localhost:5000/recognitions/1/endorse \
  -H "Content-Type: application/json" \
  -d '{"endorser_id": 3}'
```

Expected: Error response with message `"This student has already endorsed this recognition"`.

## Redemption

Students can redeem their accumulated credits and convert them into vouchers. This allows students to exchange the credits they've received from recognitions for real value.

**Business Rules:**
- Students can redeem only the credits they currently have in their balance
- Voucher value is ₹5 per credit (e.g., 10 credits = ₹50 voucher)
- Credits are permanently deducted from the student's `current_balance` upon redemption

### POST /students/<id>/redeem

Redeem credits for a student, converting them into vouchers.

**Request:**
```json
{
  "credits": 10
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "student_id": 2,
  "credits_redeemed": 10,
  "voucher_value_inr": 50,
  "created_at": "2024-01-15T12:00:00.000000"
}
```

**Error Responses:**
- `400 Bad Request` - If `credits` is missing from request body
- `400 Bad Request` - If `credits` is 0 or negative: `"credits_to_redeem must be greater than 0"`
- `400 Bad Request` - If student has insufficient credits: `"Insufficient credits. Current balance: 50, attempted to redeem: 100"`
- `400 Bad Request` - If student with the given ID doesn't exist: `"Student with id {id} not found"`

### Redemption Usage Example

**1. Check a student's balance:**
```bash
curl -X GET http://localhost:5000/students/2
```

Expected: Returns student information including `current_balance` (e.g., 110 credits).

**2. Redeem 5 credits:**
```bash
curl -X POST http://localhost:5000/students/2/redeem \
  -H "Content-Type: application/json" \
  -d '{"credits": 5}'
```

Expected: Redemption is created successfully, returning redemption details with `voucher_value_inr: 25` (5 credits × ₹5).

**3. Check balance again:**
```bash
curl -X GET http://localhost:5000/students/2
```

Expected: Student's `current_balance` has decreased by 5 credits (e.g., from 110 to 105).

**4. Try redeeming more credits than available:**
```bash
curl -X POST http://localhost:5000/students/2/redeem \
  -H "Content-Type: application/json" \
  -d '{"credits": 1000}'
```

Expected: Error response with message `"Insufficient credits. Current balance: 105, attempted to redeem: 1000"`.

## Leaderboard

The leaderboard displays the top students ranked by the total credits they have received from recognitions. This provides visibility into which students are being recognized most by their peers.

**Ranking Rules:**
- Students are sorted by `credits_received_total` in descending order (highest first)
- If two students have equal `credits_received_total`, they are sorted by `student_id` in ascending order as a tie-breaker

### GET /leaderboard?limit=10

Get the top students ranked by credits received.

**Query Parameters:**
- `limit` (optional): Number of students to return. Defaults to 10 if not provided.

**Response (200 OK):**
```json
[
  {
    "student_id": 3,
    "name": "Charlie",
    "credits_received_total": 120,
    "recognition_count": 4,
    "endorsement_count": 7
  },
  {
    "student_id": 2,
    "name": "Bob",
    "credits_received_total": 110,
    "recognition_count": 3,
    "endorsement_count": 5
  },
  {
    "student_id": 1,
    "name": "Alice",
    "credits_received_total": 50,
    "recognition_count": 2,
    "endorsement_count": 3
  }
]
```

**Response Fields:**
- `student_id`: The unique identifier of the student
- `name`: The student's name
- `credits_received_total`: Total credits the student has received from all recognitions
- `recognition_count`: Number of recognitions the student has received
- `endorsement_count`: Total number of endorsements across all recognitions received by the student

### Leaderboard Usage Examples

**1. Get default leaderboard (top 10):**
```bash
curl -X GET http://localhost:5000/leaderboard
```

**2. Get limited leaderboard (top 3):**
```bash
curl -X GET "http://localhost:5000/leaderboard?limit=3"
```

**3. Get top 20 students:**
```bash
curl -X GET "http://localhost:5000/leaderboard?limit=20"
```

The leaderboard returns an array of student objects sorted by their total credits received, making it easy to identify the most recognized students in the system.

## Monthly Credit Reset

At the start of each calendar month, all students automatically receive a credit reset. This ensures fair distribution of credits and allows students to carry forward a portion of their unused credits from the previous month.

**How Monthly Reset Works:**
- Each student receives a **base allowance of 100 credits** at the start of the month
- Up to **50 unused credits** from the previous month may be carried forward
  - Example: If a student had 140 credits remaining, only 50 are carried forward, resulting in a new balance of 150 credits (100 base + 50 carried)
  - Example: If a student had 30 credits remaining, all 30 are carried forward, resulting in a new balance of 130 credits (100 base + 30 carried)
- The `monthly_sent_this_month` counter is reset to 0
- Each reset is logged in the `MonthlyResetLog` table for audit purposes

**Automatic Reset Schedule:**
The monthly reset runs automatically via a scheduled job on the **1st day of every month at 00:05** (5 minutes past midnight). This ensures all students receive their new monthly credits at the start of each calendar month.

### GET /admin/run-monthly-reset

Manually trigger the monthly reset for all students. This endpoint is useful for testing the reset functionality without waiting for the scheduled job.

**Response (200 OK):**
```json
{
  "message": "Monthly reset completed successfully",
  "students_reset": 3
}
```

**Response Fields:**
- `message`: Confirmation message
- `students_reset`: Number of students who were reset (students who needed a reset)

**Note:** This endpoint will only reset students who haven't been reset for the current month. If a student was already reset this month, they will be skipped.

### Monthly Reset Usage Example

**1. Check a student's balance before reset:**
```bash
curl -X GET http://localhost:5000/students/2
```

Expected: Returns student information showing their current balance (e.g., 140 credits) and `monthly_sent_this_month` value.

**2. Call manual reset:**
```bash
curl -X GET http://localhost:5000/admin/run-monthly-reset
```

Expected: Returns success message with the number of students reset.

**3. Check student balance after reset:**
```bash
curl -X GET http://localhost:5000/students/2
```

Expected outcomes:
- If the student had 140 credits: New balance is 150 (100 base + 50 carried forward)
- If the student had 30 credits: New balance is 130 (100 base + 30 carried forward)
- If the student had 0 credits: New balance is 100 (100 base + 0 carried forward)
- `monthly_sent_this_month` is reset to 0

### MonthlyResetLog

The system maintains a log of all monthly resets in the `MonthlyResetLog` table. Each entry stores:
- `student_id`: The student who was reset
- `month`: The month number (1-12) when the reset occurred
- `year`: The year when the reset occurred
- `carried_forward`: The number of credits that were carried forward from the previous month
- `created_at`: Timestamp of when the reset was performed

This log provides a complete audit trail of all monthly credit resets, allowing you to track credit distribution over time.

## Next Features Coming Soon

_All core features have been implemented!_

