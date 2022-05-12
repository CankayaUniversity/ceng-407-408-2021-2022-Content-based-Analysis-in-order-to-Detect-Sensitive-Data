import os
import hashlib
import smtplib
from email import policy, parser
from flask import Flask, request, render_template

MAIL_DIR = "mails"

app = Flask(__name__)

@app.route("/submit_data", methods = ["POST"])
def submit_data():
    if request.method == "POST":
        data = request.form["data"].encode("utf-8")
        data_hash = hashlib.sha256()
        data_hash.update(data)
        filename = data_hash.hexdigest()
        with open(os.path.join(MAIL_DIR, filename), "wb") as f:
            f.write(data)

@app.route("/", methods = ["GET"])
def root():
    if request.method == "GET":
        emails = []
        filenames = []
        for filename in os.listdir(MAIL_DIR):
            with open(os.path.join(MAIL_DIR, filename), "rb") as f:
                data = f.read().decode("utf-8")
                emails.append(data)
                filenames.append(filename)
        return render_template("index.html", email_info = zip(emails, filenames))
    return None

@app.route("/send_mail", methods = ["POST"])
def send_mail():
    if request.method == "POST":
        filename = request.form["filename"]
        with open(os.path.join(MAIL_DIR, filename), "rb") as f:
            data = f.read()
            msg = parser.BytesParser(policy = policy.default).parsebytes(data)
            with smtplib.SMTP("zimbra-docker.zimbra.io") as smtp:
                smtp.sendmail(msg["from"], msg["to"], data)
            os.unlink(os.path.join(MAIL_DIR, filename))
