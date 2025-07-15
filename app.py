from flask import Flask, render_template, request, session, redirect, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_mail import Mail, Message
import secrets
import json
import os

app = Flask(__name__)
app.secret_key = 'supersecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
db = SQLAlchemy(app)
app.config['MAIL_SERVER'] = 'smtp.mail.ru'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = '9265655613@mail.ru'
app.config['MAIL_PASSWORD'] = '53xGkxZzl3y6Qr9pscGY'  # сюда подставишь свой пароль
app.config['MAIL_DEFAULT_SENDER'] = '9265655613@mail.ru'
mail = Mail(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    is_confirmed = db.Column(db.Boolean, default=False)
    confirm_token = db.Column(db.String(128), nullable=True)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    attempts = db.Column(db.Integer, nullable=False)
    seconds = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    word = db.Column(db.String(16), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD

# >>>> Главное отличие <<<<
def create_tables():
    with app.app_context():
        db.create_all()

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/game')
def game():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('game.html', username=session['username'])

@app.route('/save_result', methods=['POST'])
def save_result():
    if 'user_id' not in session:
        return 'auth required', 403
    data = request.json
    attempts = int(data.get('attempts', 0))
    seconds = int(data.get('seconds', 0))
    word = data.get('word', '')
    score = attempts * seconds
    date = datetime.now().strftime('%Y-%m-%d')
    # Один результат в день на пользователя на слово
    res = Result.query.filter_by(user_id=session['user_id'], date=date, word=word).first()
    if not res:
        res = Result(user_id=session['user_id'], attempts=attempts, seconds=seconds, score=score, word=word, date=date)
        db.session.add(res)
    else:
        if score < res.score:  # Обновляем только если лучше результат
            res.attempts = attempts
            res.seconds = seconds
            res.score = score
    db.session.commit()
    return 'ok'

@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect('/')
    user_results = Result.query.filter_by(user_id=session['user_id']).order_by(Result.date.desc()).all()
    all_results = db.session.query(Result, User).join(User, Result.user_id == User.id).order_by(Result.score.asc()).limit(50).all()
    return render_template('results.html', user_results=user_results, all_results=all_results, username=session['username'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        if not username or not email or not password or not password2:
            error = "Заполните все поля"
        elif password != password2:
            error = "Пароли не совпадают"
        elif User.query.filter_by(username=username).first():
            error = "Пользователь с таким именем уже есть"
        elif User.query.filter_by(email=email).first():
            error = "Этот email уже зарегистрирован"
        else:
            token = secrets.token_urlsafe(32)
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                email=email,
                is_confirmed=False,
                confirm_token=token
            )
            db.session.add(user)
            db.session.commit()
            confirm_url = url_for('confirm_email', token=token, _external=True)
            msg = Message(
                subject='Подтвердите регистрацию на Wordle',
                recipients=[email],
                body=f'Здравствуйте, {username}!\nПерейдите по ссылке для подтверждения: {confirm_url}',
                sender='9265655613@mail.ru'
            )
            mail.send(msg)
            return render_template('info.html', message="Проверьте e-mail для подтверждения регистрации.", login_url=url_for('login'))
    return render_template('register.html', error=error)

@app.route('/confirm/<token>')
def confirm_email(token):
    user = User.query.filter_by(confirm_token=token).first()
    if user and not user.is_confirmed:
        user.is_confirmed = True
        user.confirm_token = None
        db.session.commit()
        return render_template('info.html', message="E-mail подтверждён! Теперь можно войти.", login_url=url_for('login'))
    else:
        return render_template('info.html', message="Некорректная или уже подтверждённая ссылка.", login_url=url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        if not username or not password:
            error = "Заполните все поля"
        else:
            user = User.query.filter_by(username=username).first()
            if not user:
                error = "Пользователь не найден"
            elif not user.is_confirmed:
                error = "Сначала подтвердите e-mail!"
            elif not check_password_hash(user.password_hash, password):
                error = "Неверный пароль"
            else:
                session['user_id'] = user.id
                session['username'] = user.username
                return redirect('/game')
    return render_template('login.html', error=error)

@app.route('/')
def index():
    return redirect(url_for('login'))

if __name__ == '__main__':
    create_tables()  # <-- вызывается ОДИН РАЗ перед запуском сервера!
    app.run(debug=True)