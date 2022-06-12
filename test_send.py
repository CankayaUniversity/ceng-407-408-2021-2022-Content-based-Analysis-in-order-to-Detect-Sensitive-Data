import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

smtp = smtplib.SMTP()
smtp.connect("localhost")

msgRoot = MIMEMultipart("alternative")
msgRoot["Subject"] = Header("Subject subject", "utf-8")
msgRoot["From"] = "admin@test.local"
msgRoot["To"] = "admin@zimbra.io"
text = MIMEText(open("./template.txt", 'r').read(), "plain", "utf-8")
msgRoot.attach(text)
smtp.sendmail("admin@test.local", "admin@zimbra.io", msgRoot.as_string())
