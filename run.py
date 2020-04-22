import pymorphy2
import re
from flask import Flask
from flask import render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, StringField
from wtforms.validators import DataRequired
from datetime import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = 'a really really really really long secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:postgres@localhost/dictionary'

db = SQLAlchemy(app)
morph = pymorphy2.MorphAnalyzer()


class Lexeme(db.Model):
    __tablename__ = 'lexemes'
    id = db.Column(db.Integer(), primary_key=True)
    normal_form = db.Column(db.String(40), nullable=False)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(
        db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    words = db.relationship('Word', backref='lexeme')


class Word(db.Model):
    __tablename__ = 'words'
    id = db.Column(db.Integer(), primary_key=True)
    word = db.Column(db.String(40), nullable=False)
    comment = db.Column(db.String(255))
    score = db.Column(db.Float, nullable=False)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(
        db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    lexeme_id = db.Column(db.Integer(), db.ForeignKey('lexemes.id'))


class TextAnalysisForm(FlaskForm):
    text = TextAreaField("Текст", validators=[DataRequired()])
    submit = SubmitField("Ввод")


class AddWordForm(FlaskForm):
    word = StringField("Слово:", validators=[DataRequired()])
    comment = TextAreaField("Комментарий")
    submit = SubmitField("Ввод")


class WordCommentForm(FlaskForm):
    comment = TextAreaField("Комментарий")
    submit = SubmitField("Ввод")


@app.route('/')
def index():
    return redirect(url_for('help'))


@app.route('/analysis/', methods=['get', 'post'])
def analysis():
    form = TextAnalysisForm()
    if form.validate_on_submit():
        text = form.text.data
        word_list = re.sub("[.,?!'\";:-]+", "", text).lower().split()
        word_form_list = set(word_list)
        for word in word_form_list:
            word_parse = morph.parse(word)[0]
            query = db.session.query(Word).filter(Word.word == word).first()
            if query:
                new_word = query
            else:
                new_word = Word(word=word, score=word_parse.score)
                lexeme = word_parse.lexeme[0].normal_form
                query = db.session.query(Lexeme).filter(
                    Lexeme.normal_form == lexeme).first()
                if query:
                    new_word.lexeme = query
                else:
                    new_lexeme = Lexeme(normal_form=lexeme)
                    new_word.lexeme = new_lexeme
            db.session.add(new_word)
        db.session.commit()
        return redirect(url_for('analysis'))
    return render_template('analysis.html', form=form)


@app.route('/lexemes/')
def lexemes():
    lexemes = db.session.query(Lexeme).order_by(Lexeme.normal_form).all()
    return render_template("lexemes.html", lexemes=lexemes)


@app.route('/words/')
def words():
    words = db.session.query(Word).order_by(Word.word).all()
    return render_template("words.html", words=words)


@app.route('/words/add', methods=['get', 'post'])
def add_word():
    form = AddWordForm()
    if form.validate_on_submit():
        word_data = form.word.data.lower()
        comment_data = form.comment.data
        word_parse = morph.parse(word_data)[0]
        query = db.session.query(Word).filter(Word.word == word_data).first()
        if query:
            new_word = query
        else:
            new_word = Word(word=word_data, comment=comment_data,
                            score=word_parse.score)
            lexeme = word_parse.lexeme[0].normal_form
            query = db.session.query(Lexeme).filter(
                Lexeme.normal_form == lexeme).first()
            if query:
                new_word.lexeme = query
            else:
                new_lexeme = Lexeme(normal_form=lexeme)
                new_word.lexeme = new_lexeme
        db.session.add(new_word)
        db.session.commit()
        return redirect(url_for('words'))
    return render_template('add_word.html', form=form)


@app.route('/words/<int:id>/edit/', methods=['get', 'post'])
def edit_word(id):
    word = db.session.query(Word).filter(Word.id == id).first()
    form = WordCommentForm()
    if form.validate_on_submit():
        comment = form.comment.data
        word.comment = comment
        db.session.add(word)
        db.session.commit()
        return redirect(url_for('words'))
    else:
        form.comment.data = word.comment
        return render_template('edit_word.html', word=word.word, form=form)


@app.route('/words/<int:id>/delete', methods=['get', 'post'])
def delete_word(id):
    word = db.session.query(Word).filter(Word.id == id).first()
    if request.method == 'POST':
        db.session.delete(word)
        db.session.commit()
        return redirect(url_for('words'))
    else:
        return render_template('delete_word.html', word=word.word)


@app.route('/help/')
def help():
    return render_template('help.html')


if __name__ == '__main__':
    app.run(debug=True)
