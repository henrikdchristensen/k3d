import psycopg2
import psycopg2.extras
from faker import Faker
import uuid
import random
import bcrypt
from config import DB_CONFIG

def populate_fake_data(num_users=20, num_challenges=10, num_competitions=5, max_competitions_per_user=3):
    """Populate tables with fake data."""
    fake = Faker()
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # Insert fake competitions
        competition_ids = []
        for _ in range(num_competitions):
            comp_id = str(uuid.uuid4())
            name = fake.catch_phrase()
            active = random.choice([True, False])
            cursor.execute(
                """
                INSERT INTO competitions (id, name, active)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (comp_id, name, active)
            )
            competition_ids.append(comp_id)

        # Insert a user role explicitly
        user_username = "user1"
        user_email = "user1@gmail.com"
        user_password = bcrypt.hashpw("pass123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user_role = "user"
        cursor.execute(
            """
            INSERT INTO users (username, password_hashed, email, role)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (user_username, user_password, user_email, user_role)
        )
        
        # Insert a developer role explicitly
        dev_username = "developer1"
        dev_email = "developer1@gmail.com"
        dev_password = bcrypt.hashpw("pass123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        dev_role = "developer"
        cursor.execute(
            """
            INSERT INTO users (username, password_hashed, email, role)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (dev_username, dev_password, dev_email, dev_role)
        )
        
        # Insert an admin role explicitly
        admin_username = "admin1"
        admin_email = "admin1@gmail.com"
        admin_password = bcrypt.hashpw("pass123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_role = "admin"
        cursor.execute(
            """
            INSERT INTO users (username, password_hashed, email, role)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
            """,
            (admin_username, admin_password, admin_email, admin_role)
        )

        # Insert fake users
        usernames = [user_username, dev_username, admin_username]  # start with the admin user
        for _ in range(num_users - 3):  # subtract 3 to account for the static defined users
            username = fake.user_name()
            email = fake.email()
            role = "user" # all other users are just users
            password = fake.password()
            cursor.execute(
                """
                INSERT INTO users (username, password_hashed, email, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (username, password, email, role)
            )
            usernames.append(username)

        # Assign each user to multiple competitions
        participants = []
        for username in usernames:
            num_competitions = random.randint(1, max_competitions_per_user)
            user_competitions = random.sample(competition_ids, num_competitions)
            for competition_id in user_competitions:
                cursor.execute(
                    """
                    INSERT INTO participants (username, competition_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (username, competition_id)
                )
                participants.append((username, competition_id))

        # Insert challenges
        challenges = []
        for comp_id in competition_ids:
            for _ in range(random.randint(5, num_challenges)):
                challenge_id = str(uuid.uuid4())
                name = fake.word()
                description = fake.sentence()
                category = random.choice(["crypto", "web", "pwn", "misc"])
                difficulty = random.choice(["easy", "medium", "hard"])
                flag_format = f"FLAG{{{str(uuid.uuid4())[:10]}}}"
                author = fake.name()
                flag = str(uuid.uuid4())
                score = random.randint(100, 1000)
                testing = random.choice([True, False])
                ready = random.choice([True, False])
                image_url = fake.image_url()
                cursor.execute(
                    """
                    INSERT INTO challenges (id, name, description, category, difficulty, flag_format, author, flag, resource_limits, score, testing, ready, image_url, competition_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (challenge_id, name, description, category, difficulty, flag_format, author, flag, "None", score, testing, ready, image_url, comp_id)
                )
                challenges.append((challenge_id, comp_id))

        # Insert submissions
        for challenge_id, comp_id in challenges:
            for _ in range(random.randint(5, 10)):
                username = random.choice(usernames)
                if (username, comp_id) not in participants:
                    continue
                timestamp = fake.date_time_this_year()
                submission_flag = fake.word()
                score = random.randint(50, 500)
                admin = random.choice([True, False])
                valid = random.choice([True, False])
                cursor.execute(
                    """
                    INSERT INTO submissions (username, competition_id, challenge_id, timestamp, submission_flag, score, admin, valid)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (username, comp_id, challenge_id, timestamp, submission_flag, score, admin, valid)
                )

        conn.commit()
        print(f"Inserted {num_users} users, {num_challenges} challenges, {num_competitions} competitions, participants, and submissions.")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    populate_fake_data()
