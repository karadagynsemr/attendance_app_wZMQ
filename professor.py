import zmq
import psycopg2
from datetime import datetime

DB_NAME = "attendance_db"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5432"

professor_username = 'admin'
professor_password = 'admin'

def get_db_connection():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    return conn

def check_admin():
    username = input("Username: ")
    password = input("Password: ")
    if username != professor_username or password != professor_password:
        print("Invalid username or password!!!")
        return check_admin()
    else:
        return True

# Take attendance
def get_attendance():
    session_date = datetime.now().strftime("%Y-%m-%d")
    if check_admin() == True:
        context = zmq.Context()
        replier = context.socket(zmq.REP)
        port = 5555
        server_address = f"tcp://*:{port}"
        replier.bind(server_address)
        print("Server is running, waiting for attendees...")
        print("Press 'Ctrl+C' to finish attendance.")

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            while True:
                message = replier.recv_string()
                full_name, student_id = message.split(" - ")

                # Check student
                cur.execute("SELECT full_name, absence_right FROM students WHERE student_id = %s", (student_id,))
                student = cur.fetchone()
                if not student:
                    replier.send_string("ERROR: You are not registered for this course!")
                    continue

                db_full_name, absence_right = student
                if full_name != db_full_name:
                    replier.send_string("ERROR: Name and ID do not match!")
                    continue

                cur.execute(
                    "SELECT 1 FROM attendances WHERE student_id = %s AND attendance_date = %s",
                    (student_id, session_date)
                )
                if cur.fetchone():
                    replier.send_string(f"ERROR: {student_id} already registered!!!")
                    continue

                else:
                    cur.execute(
                        "INSERT INTO attendances (student_id, attendance_date) VALUES (%s, %s)",
                        (student_id, session_date)
                    )
                    print(f"{full_name} - {student_id} attended.")
                conn.commit()


                reply = f"Attendance recorded successfully. Remaining absence rights: {absence_right}"
                if absence_right < 0:
                    reply = "You failed the course due to excessive absences!"
                replier.send_string(reply)

        except KeyboardInterrupt:
            print("\nAttendance Results for", session_date)

            cur.execute("""
                        UPDATE students
                        SET absence_right = absence_right - 1
                        WHERE student_id NOT IN (
                            SELECT student_id
                            FROM attendances
                            WHERE attendance_date = %s
                        )
                        """, (session_date,))
            conn.commit()


            cur.execute(
                "SELECT s.full_name, s.student_id FROM students s JOIN attendances a ON s.student_id = a.student_id WHERE a.attendance_date = %s",
                (session_date,)
            )
            attenders = cur.fetchall()
            for full_name, student_id in attenders:
                print(f"{full_name} - {student_id}")
            print(f"Total attendees = {len(attenders)}")

            conn.close()
            replier.close()
            context.term()

while True:
    print("\n1. Start attendance\n2. Exit")
    choice = input("Choose an option: ")
    if choice == '1':
        get_attendance()
    elif choice == '2':
        break