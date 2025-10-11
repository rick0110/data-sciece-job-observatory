from flask import Flask, render_template
import json

global context
context = json.load(open('./static/images/dashboard_context.json'))
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', **context)


if __name__ == '__main__':
    app.run(debug=True)