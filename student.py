import zmq
from flask import Flask, render_template, request
import psycopg2

attendance_app = Flask('attendance_web_app')

DB_NAME = "attendance_db"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5432"

def get_db_connection():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    return conn



context = zmq.Context()
requester = context.socket(zmq.REQ)
receiver_port = 5555
server_address = f"tcp://10.50.17.52:{receiver_port}"
requester.connect(server_address)

def send_attendance(full_name, student_id):
    if not full_name or not student_id:
        return "ERROR: Full name and student ID cannot be empty!"

    message = f"{full_name} - {student_id}"
    requester.send_string(message)

    poller = zmq.Poller()
    poller.register(requester, zmq.POLLIN)
    if poller.poll(5000):
        reply = requester.recv_string()
        if reply == "Attendance recorded successfully.":
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT absence_right FROM students WHERE student_id = %s", (student_id,))
            absence_right = cur.fetchone()[0]
            conn.close()
            return f"Attendance recorded successfully. Remaining absence rights: {absence_right}"
    else:
        reply = "ERROR: ZMQ server timeout!"
    return reply

@attendance_app.route('/', methods=['GET', 'POST'])
def attendance_form():
    message = None
    error = None
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        student_id = request.form.get('student_id')
        result = send_attendance(full_name, student_id)
        if (result.startswith("ERROR:") or result.startswith("You failed")):
            error = result
        else:
            message = result
    return render_template('student_attendance.html', message=message, error=error)

if __name__ == '__main__':
    attendance_app.run(host='0.0.0.0', port=5001)