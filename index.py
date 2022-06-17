from app import app
from webhooks import *
from tokens import *
from files import *

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
