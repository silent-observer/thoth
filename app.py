import os
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"