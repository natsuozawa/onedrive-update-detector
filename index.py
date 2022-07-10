from app import app
from webhooks import *
from tokens import *
from files import *

if __name__ == '__main__':
  if app.config["MDOE"] == "debug":
    app.run(host="0.0.0.0", port=5000, debug=True)
  else:
    app.run(host="0.0.0.0", port=5000)
