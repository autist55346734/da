from flask import Flask, render_template, url_for, redirect
from data import db_session
from data.user import User
from data.task import Task
from forms.users import RegisterForm, LoginForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'movavi_is_the_best_it_school'


@app.route('/')
def home_page():
    return render_template('index.html', title='Главная', img=url_for('static', filename='img/monkey.png'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form, message="Такой пользователь уже есть",
                                   img=url_for('static', filename='img/monkey.png'))
        user = User(
            nickname=form.nickname.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form,
                           img=url_for('static', filename='img/monkey.png'))


def main():
    db_session.global_init("db/punch.sqlite")
    app.run()


if __name__ == '__main__':
    main()