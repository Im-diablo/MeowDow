from flask import Flask # type: ignore
app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'This is test server'


if __name__ == "__main__":
    app.run(debug=True,threaded=False,host="0.0.0.0")