from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return " This is Room Tag Predictor <h3>(RTP)</h3> Homepage. "

@app.route("/<name>")
def user(name):
    return "Hello {}!".format(name)


if __name__ == "__main__":
    app.run()