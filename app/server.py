from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send
import eventlet

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

players = {}

# Пример данных для вопросов и ответов
questions = {
    'География': [
        ('Столица России?', 'Москва'),
        ('Столица Франции?', 'Париж'),
        ('Столица Японии?', 'Токио')
    ],
    'История': [
        ('Год начала Второй мировой войны?', '1939'),
        ('Год окончания Второй мировой войны?', '1945'),
        ('Год начала Первой мировой войны?', '1914')
    ],
    'Спорт': [
        ('Сколько игроков в футбольной команде?', '11'),
        ('Сколько игроков в баскетбольной команде?', '5'),
        ('Сколько игроков в хоккейной команде?', '6')
    ],
    'Литература': [
        ('Автор романа "Война и мир"?', 'Лев Толстой'),
        ('Автор романа "Преступление и наказание"?', 'Федор Достоевский'),
        ('Автор романа "Мастер и Маргарита"?', 'Михаил Булгаков')
    ],
    'Экономика': [
        ('Что такое инфляция?', 'Повышение общего уровня цен'),
        ('Что такое дефляция?', 'Понижение общего уровня цен'),
        ('Что такое ВВП?', 'Валовой внутренний продукт')
    ]
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/gamecat')
def gamecat():
    return render_template('gamecat.html')

@app.route('/game')
def game():
    category = request.args.get('category')
    if category in questions:
        return render_template('game.html', category=category)
    else:
        return "Invalid category", 400

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
    _, correct_answer = questions[category][question_index]
    if answer.strip().lower() == correct_answer.lower():
        players[username]['score'] += 1
    players[username]['question_index'] += 1
    next_question(username, room)

def next_question(username, room):
    category = players[username]['category']
    question_index = players[username]['question_index']
    if question_index < len(questions[category]):
        question, _ = questions[category][question_index]
        socketio.emit('next_question', {'question': question}, to=room)
    else:
        score = players[username]['score']
        socketio.emit('show_results', {'score': score, 'total': len(questions[category])}, to=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)