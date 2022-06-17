from flask import Flask
import requests

app = Flask(__name__)
app.config.from_pyfile('app.cfg')
