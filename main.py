import eventlet
import socketio
from eventlet import wsgi
from loguru import logger
from src.all_riddles import riddles
from random import choice


class Riddle:
    def __init__(self, number, text, answer):
        self.number = number
        self.text = text
        self.answer = answer

class Player:
    def __init__(self, sid):
        self.sid = sid
        self.score = 0
        self.current_riddle = None

    def answer_riddle(self, answer):
        if self.current_riddle and answer.lower() == self.current_riddle.answer.lower():
            self.score += 1
            return True
        return False

# Заставляем работать пути к статике
static_files = {'/': 'static/index.html', '/static': './static'}
sio = socketio.Server(cors_allowed_origins='*', async_mode='eventlet')
app = socketio.WSGIApp(sio, static_files=static_files)

players = {}

# Обрабатываем подключение пользователя
@sio.event
def connect(sid, environ):
    logger.info(f"Пользователь {sid} подключился")
    players[sid] = Player(sid)

# Обрабатываем запрос очередного вопроса
@sio.on('next')
def next_event(sid, data):
    player = players.get(sid)
    if player is None:
        return

    if len(riddles) == 0:
        sio.emit('over', to=sid)
        return

    # Выбираем случайную загадку
    chosen_riddle = choice(riddles)
    player.current_riddle = Riddle(**chosen_riddle)
    riddles.remove(chosen_riddle)  # удаляем загадку из списка для уникальности

    # Отправляем новую загадку клиенту
    sio.emit('riddle', {'text': player.current_riddle.text}, to=sid)

# Обрабатываем отправку ответа
@sio.on('answer')
def receive_answer(sid, data):
    player = players.get(sid)
    if player is None or player.current_riddle is None:
        return

    is_correct = player.answer_riddle(data.get("text"))
    result = {
        'text': player.current_riddle.text,
        'is_correct': is_correct,
        'answer': player.current_riddle.answer
    }

    if is_correct:
        sio.emit('score', {'value': player.score}, to=sid)

    # Отправляем результат пользователю
    sio.emit('result', result, to=sid)

# Обрабатываем отключение пользователя
@sio.event
def disconnect(sid):
    logger.info(f"Пользователь {sid} отключился")
    if sid in players:
        del players[sid]

if __name__ == '__main__':
    wsgi.server(eventlet.listen(("127.0.0.1", 8000)), app)