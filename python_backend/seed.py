from sqlalchemy.orm import Session
from models import BankService, Counter, Token, User
from auth import hash_password


def seed_database(db: Session):
    # Check if already seeded
    if db.query(BankService).count() > 0:
        return

    print("Seeding Bank Queue Database...")

    # 1. Services
    services_data = [
        {"code": "DEP", "name": "Cash Deposit", "description": "Deposit cash safely into your account.", "estimated_time": "8 min", "duration_minutes": 8, "prefix": "A", "icon": "banknote"},
        {"code": "WTH", "name": "Cash Withdrawal", "description": "Withdraw cash with assisted counter service.", "estimated_time": "10 min", "duration_minutes": 10, "prefix": "A", "icon": "credit-card"},
        {"code": "ACC", "name": "Account Opening", "description": "Open a new savings or current account.", "estimated_time": "25 min", "duration_minutes": 25, "prefix": "B", "icon": "wallet-cards"},
        {"code": "PBK", "name": "Passbook Update", "description": "Update and print your latest transactions.", "estimated_time": "5 min", "duration_minutes": 5, "prefix": "D", "icon": "file-text"},
        {"code": "CHQ", "name": "Cheque Services", "description": "Cheque deposit, clearing and related support.", "estimated_time": "12 min", "duration_minutes": 12, "prefix": "C", "icon": "check-square"},
        {"code": "CRD", "name": "ATM / Debit Card", "description": "Card issue, replacement and PIN assistance.", "estimated_time": "15 min", "duration_minutes": 15, "prefix": "C", "icon": "credit-card"},
        {"code": "OTH", "name": "Other Services", "description": "General customer service and inquiries.", "estimated_time": "15 min", "duration_minutes": 15, "prefix": "B", "icon": "help-circle"},
    ]

    services = []
    for s in services_data:
        srv = BankService(**s)
        db.add(srv)
        services.append(srv)
    db.commit()

    # 2. Counters
    counters_data = [
        {"name": "Counter 1", "desk_label": "Cash services", "description": "High-volume cash deposit and withdrawals", "status": "ONLINE", "staff_name": "Ramesh Kumar"},
        {"name": "Counter 2", "desk_label": "Account Services", "description": "New account openings and customer KYC", "status": "ONLINE", "staff_name": "Priya Sharma"},
        {"name": "Counter 3", "desk_label": "Cheque & Card Desk", "description": "Cheque deposit, clearing, and debit cards", "status": "ONLINE", "staff_name": "Vikram Singh"},
        {"name": "Counter 4", "desk_label": "Quick Services & Passbook", "description": "Passbook updates and general inquiries", "status": "ONLINE", "staff_name": "Sneha Patel"},
    ]

    counters = []
    for c in counters_data:
        cnt = Counter(**c)
        db.add(cnt)
        counters.append(cnt)
    db.commit()

    # 3. Seed Users for All 3 Roles: Admin, Employee (Staff), Customer
    users_to_seed = [
        User(
            full_name="Bank Administrator",
            phone="+919876543201",
            email="admin@bankqueue.example",
            password_hash=hash_password("Password123"),
            role="ADMIN",
        ),
        User(
            full_name="Branch Manager",
            phone="+919876543210",
            email="manager@bankqueue.example",
            password_hash=hash_password("Password123"),
            role="ADMIN",
        ),
        User(
            full_name="Ramesh Kumar (Bank Employee)",
            phone="+919876543202",
            email="staff@bankqueue.example",
            password_hash=hash_password("Password123"),
            role="STAFF",
        ),
        User(
            full_name="Priya Sharma (Bank Employee)",
            phone="+919876543203",
            email="employee@bankqueue.example",
            password_hash=hash_password("Password123"),
            role="STAFF",
        ),
        User(
            full_name="Customer User",
            phone="+919876543204",
            email="customer@bankqueue.example",
            password_hash=hash_password("Password123"),
            role="CUSTOMER",
        ),
        User(
            full_name="Rohit Sharma",
            phone="+919876543211",
            email="rohit@example.com",
            password_hash=hash_password("Password123"),
            role="CUSTOMER",
        ),
    ]
    for u in users_to_seed:
        db.add(u)
    db.commit()

    # 4. Seed Tokens matching the website demonstration
    tokens_data = [
        {
            "token_number": "A104",
            "service_id": services[0].id,
            "counter_id": counters[0].id,
            "customer_name": "Ananya Rao",
            "customer_phone": "+919876500104",
            "booking_date": "Today",
            "time_slot": "10:15 AM",
            "status": "SERVING",
            "estimated_wait_minutes": 0,
            "recommended_arrival_time": "10:15 AM",
        },
        {
            "token_number": "A105",
            "service_id": services[0].id,
            "counter_id": counters[0].id,
            "customer_name": "Karthik Verma",
            "customer_phone": "+919876500105",
            "booking_date": "Today",
            "time_slot": "10:30 AM",
            "status": "APPROACHING",
            "estimated_wait_minutes": 8,
            "recommended_arrival_time": "10:25 AM",
        },
        {
            "token_number": "A106",
            "service_id": services[1].id,
            "counter_id": counters[0].id,
            "customer_name": "Siddharth Jain",
            "customer_phone": "+919876500106",
            "booking_date": "Today",
            "time_slot": "10:45 AM",
            "status": "WAITING",
            "estimated_wait_minutes": 18,
            "recommended_arrival_time": "10:40 AM",
        },
        {
            "token_number": "A108",
            "service_id": services[0].id,
            "counter_id": counters[0].id,
            "customer_name": "Meera Patel",
            "customer_phone": "+919876500108",
            "customer_email": "meera@example.com",
            "customer_account_number": "48920193821",
            "booking_date": "Today",
            "time_slot": "10:30 AM",
            "status": "APPROACHING",
            "estimated_wait_minutes": 12,
            "recommended_arrival_time": "10:20 AM",
        },
        {
            "token_number": "B201",
            "service_id": services[2].id,
            "counter_id": counters[1].id,
            "customer_name": "Arjun Menon",
            "customer_phone": "+919876500201",
            "booking_date": "Today",
            "time_slot": "10:00 AM",
            "status": "SERVING",
            "estimated_wait_minutes": 0,
            "recommended_arrival_time": "10:00 AM",
        },
        {
            "token_number": "C102",
            "service_id": services[4].id,
            "counter_id": counters[2].id,
            "customer_name": "Neha Gupta",
            "customer_phone": "+919876500302",
            "booking_date": "Today",
            "time_slot": "11:00 AM",
            "status": "WAITING",
            "estimated_wait_minutes": 15,
            "recommended_arrival_time": "10:50 AM",
        },
    ]

    for t_data in tokens_data:
        t = Token(**t_data)
        db.add(t)
    db.commit()

    # Link current tokens to counters
    counters[0].current_token_id = db.query(Token).filter(Token.token_number == "A104").first().id
    counters[1].current_token_id = db.query(Token).filter(Token.token_number == "B201").first().id
    db.commit()
    print("Database seeded successfully with initial data matching https://queue-wiz-home.lovable.app")
