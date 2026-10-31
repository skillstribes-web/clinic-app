from flask import Flask

web = Flask(__name__)


@web.route("/")
def home():
    return "<h1>Clinic Appointment App</h1><p>Website chal rahi hai!</p>"


web.run(debug=True)