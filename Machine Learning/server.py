from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return " This is <h3>Plug In homepage </h3>"

@app.route("/<name>")
def user(name):
    return "Hello {}!".format(name)


if __name__ == "__main__":
    app.run()