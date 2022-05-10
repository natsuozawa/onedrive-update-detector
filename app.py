from flask import Flask, render_template

app = Flask(__name__)
app.config.from_pyfile('app.cfg')

@app.route("/")
def index():
    scope = "%20".join(['offline_access', 'files.read'])
    # return "true"
    return render_template('index.html', application_id=app.config['APPLICATION_ID'], redirect_url=app.config['REDIRECT_URL'], scope=scope) 