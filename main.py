from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from urllib.parse import unquote
import os
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy



app = Flask(__name__)

# Настройка базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'  # Используйте SQLite или другую базу данных
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)

app.config['SECRET_KEY'] = 'your_secret_key'
csrf = CSRFProtect(app)
socketio = SocketIO(app)

app.config['UPLOAD_FOLDER'] = 'static/avatars/'
app.config['SECRET_KEY'] = 'secret!'

users = {
    'username': 'leoni',
    'name': 'Леонид',
    'email': 'leoni@leoni.ru',
    'avatar': '/static/img/ava2.jpg'
}
@app.route('/profile',  methods=['GET', 'POST'])
def profile():
    return render_template('profile.html', user=users)


@app.route('/update_name', methods=['POST'])
def update_name():
    new_name = request.json.get('name')
    if new_name:
        users['name'] = new_name
        return jsonify(success=True)
    return jsonify(success=False)


@app.route('/update_email', methods=['POST'])
def update_email():
    new_email = request.json.get('email')
    if new_email:
        users['email'] = new_email
        return jsonify(success=True)
    return jsonify(success=False)


@app.route('/update_avatar', methods=['POST'])
def update_avatar():
    if 'avatar' not in request.files:
        return jsonify(success=False)

    file = request.files['avatar']
    if file.filename == '':
        return jsonify(success=False)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        users['avatar'] = '/' + filepath.replace('\\', '/')
        return jsonify(success=True, new_avatar_url=users['avatar'])

    return jsonify(success=False)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    question = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(255), nullable=False)
    answer1 = db.Column(db.String(255), nullable=False)
    answer2 = db.Column(db.String(255), nullable=False)
    answer3 = db.Column(db.String(255), nullable=False)
    answer4 = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Question {self.question}>'

players = {}

questions = {

    'География': [
        {'question': 'Столица России?', 'correct_answer': 'Москва',
         'answers': ['Москва', 'Берлин', 'Лондон', 'Ташкент']},
        # Дополнительные вопросы
        {'question': 'Какая река самая длинная в мире?', 'correct_answer': 'Нил',
         'answers': ['Амазонка', 'Нил', 'Миссисипи', 'Янцзы']},
        {'question': 'Какой океан самый большой?', 'correct_answer': 'Тихий океан',
         'answers':['Атлантический океан', 'Тихий океан', 'Индийский океан', 'Северный Ледовитый океан']},
        {'question': 'В какой стране находится Мачу-Пикчу?', 'correct_answer':'Перу',
         'answers':['Чили', 'Бразилия', 'Перу', 'Колумбия']},
        {'question': 'Какая пустыня самая большая в мире?', 'correct_answer':'Сахара',
         'answers':['Гоби', 'Калахари', 'Сахара', 'Аравийская']},
        {'question': 'Какая столица Австралии?', 'correct_answer':'Канберра',
         'answers':['Сидней', 'Мельбурн', 'Канберра', 'Брисбен']},
        {'question': 'Какая страна самая большая по площади?', 'correct_answer':'Россия',
         'answers':['Канада', 'Китай', 'США', 'Россия']},
        {'question': 'На каком континенте находится пустыня Сахара?', 'correct_answer':'Африка',
         'answers':['Азия', 'Южная Америка', 'Африка', 'Австралия']},
        {'question': 'Какой самый высокий водопад в мире?', 'correct_answer':'Анхель',
         'answers':['Ниагарский водопад', 'Виктория', 'Анхель', 'Игуаcу']},
        {'question': 'Какой город является столицей Японии?', 'correct_answer':'Токио',
         'answers':['Осака', 'Киото', 'Хиросима', 'Токио']},
    ],
    'История': [
               # Вопросы по истории
    ],
    'Спорт': [
        # Вопросы по спорту
    ],
    'Литература': [
        # Вопросы по литературе
    ],
    'Экономика': [
        # Вопросы по экономике
    ]
}
@app.route('/game')
def game():
    category = request.args.get('category')
    if category in questions:
        return render_template('game.html', category=category)
    else:
        return "Invalid category", 400

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/gamecat')
def gamecat():
    return render_template('gamecat.html')

@app.route('/reg')
def reg():
    return render_template('reg.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    players[username] = {'room': room, 'score': 0, 'question_index': 0}
    send(username + ' has entered the room.', to=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    send(username + ' has left the room.', to=room)

@socketio.on('start_quiz')
def start_quiz(data):
    username = data['username']
    room = data['room']
    category = data['category']
    players[username]['category'] = category
    players[username]['question_index'] = 0
    players[username]['score'] = 0
    next_question(username, room)

@socketio.on('answer')
def check_answer(data):
    username = data['username']
    room = data['room']
    answer = data['answer']
    category = players[username]['category']
    question_index = players[username]['question_index']
    correct_answer = questions[category][question_index][1]
    if answer.strip().lower() == correct_answer.lower():
        players[username]['score'] += 1
    players[username]['question_index'] += 1
    next_question(username, room)

@socketio.on('skip_question')
def skip_question(data):
    username = data['username']
    room = data['room']
    players[username]['question_index'] += 1
    next_question(username, room)

def next_question(username, room):
    category = players[username]['category']
    question_index = players[username]['question_index']
    if question_index < len(questions[category]):
        question_data = questions[category][question_index]
        question = question_data['question']
        answers = question_data['answers']
        socketio.emit('next_question', {'question': question, 'answers': answers}, to=room)
    else:
        score = players[username]['score']
        socketio.emit('show_results', {'score': score, 'total': len(questions[category])}, to=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)


