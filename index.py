from app import app
from webhooks import *
from tokens import *
from files import *
from waitress import serve

if __name__ == '__main__':
  if app.config["MODE"] == "debug":
    app.run(host="0.0.0.0", port=5000, debug=True)
  elif app.config["MODE"] == "production":
    serve(app, host="0.0.0.0", port=5000)
  else:
    app.run(host="0.0.0.0", port=5000)
