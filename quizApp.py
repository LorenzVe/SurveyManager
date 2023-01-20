from flask import Flask, render_template, redirect, url_for, request, Response, session
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Email, Length

from markupsafe import escape
import random, copy, io, string
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///datab/survey.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'Reallysecretkey'

db = SQLAlchemy(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

scheduler = BackgroundScheduler()


# ---------------------------- LOGIN -------------------------- #
class LoginForm(FlaskForm):
	username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])
	remember = BooleanField('remember me')

class RegisterForm(FlaskForm):
	firstname = StringField('First name', validators=[InputRequired(), Length(min=4, max=32)])
	lastname = StringField('Last name', validators=[InputRequired(), Length(min=4, max=32)])
	username = StringField('Username', validators=[InputRequired(), Length(min=4, max=32)])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])

class User(UserMixin, db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	firstname = db.Column(db.String(32))
	lastname = db.Column(db.String(32))
	username = db.Column(db.String(32), unique=True)
	password = db.Column(db.String(80))

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))

# ---------------------------- SURVEY -------------------------- #
class Survey(db.Model):
	__tablename__ = 'surveys'
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(32))
	body = db.Column(db.String(1000))
	admin_id = db.Column(db.Integer)
	start_time = db.Column(db.DateTime)
	status = db.Column(db.Boolean)
	end_time = db.Column(db.DateTime)

class Question(db.Model):
	__tablename__ = 'questions'
	id = db.Column(db.Integer, primary_key=True)
	body = db.Column(db.String(100))
	survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id'))

class Answer(db.Model):
	__tablename__ = 'answers'
	id = db.Column(db.Integer, primary_key=True)
	body = db.Column(db.String(50))
	question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
	survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id'))
	is_correct = db.Column(db.Boolean())

# ---------------------------- INVITATION -------------------------- #
class Invitation(db.Model):
	__tablename__ = 'invitations'
	id = db.Column(db.Integer, primary_key=True)
	admin_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	admin_username = db.Column(db.String, db.ForeignKey('users.username'))
	participant_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id'))

class Token(db.Model):
	__tablename__ = 'tokens'
	id = db.Column(db.Integer, primary_key=True)
	token_key = db.Column(db.String(16))
	used = db.Column(db.Integer)
	available = db.Column(db.Integer)
	survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id'))

class UserAnswer(db.Model):
	__tablename__ = "user_answers"
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id'))
	question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
	answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'))
	is_correct = db.Column(db.Boolean())


@app.route('/')
def index():
	print(current_user.is_authenticated, "current user")
	user = User.query.get(2)
	print(user.is_authenticated, "User")

	return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm()

	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data).first()
		if user:
			if check_password_hash(user.password, form.password.data):
				login_user(user, remember=form.remember.data)
				return redirect(url_for('dashboard'))

		return '<h1>Invalid username or password</h1>'

	return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm()

	if form.validate_on_submit():
		hashed_password = generate_password_hash(form.password.data, method='sha256')
		new_user = User(firstname=form.firstname.data, lastname=form.lastname.data, username=form.username.data, password=hashed_password)
		db.session.add(new_user)
		db.session.commit()

		return redirect(url_for('login'))

	return render_template('register.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
	surveys = Survey.query.filter_by(admin_id=current_user.id)
	invitations = Invitation.query.filter_by(participant_id=current_user.id)

	return render_template('dashboard.html', firstname=current_user.firstname, surveys=surveys, invitations=invitations)


@app.route('/survey/<survey_id>')
@login_required
def survey(survey_id):
	survey = Survey.query.get(survey_id)
	questions = Question.query.filter_by(survey_id=survey.id)
	answers = Answer.query.filter_by(survey_id=survey.id)
	users = User.query.filter(User.id != survey.admin_id)
	user_answers = UserAnswer.query.filter_by(survey_id=survey_id)
	token = Token.query.filter_by(survey_id=survey_id)

	participants_ids = []
	invites = Invitation.query.filter_by(survey_id=survey_id)
	for i in invites:
		participants_ids.append(i.participant_id)
	participants = User.query.filter(User.id.in_(participants_ids)).all()

	is_available = False
	if survey.start_time:
		if survey.start_time <= datetime.now() <= survey.end_time:
			is_available = True
		else:
			is_available = False

	results = []
	is_plotable = False
	if user_answers.count() != 0:
		results = get_results_of(survey_id)
		is_plotable = True

	return render_template('survey.html', survey=survey, questions=questions, answers=answers, users=users, participants=participants, is_available=is_available, results=results, is_plotable=is_plotable, token=token)

def get_results_of(survey_id):
	questions = Question.query.filter_by(survey_id=survey_id)
	invitations = Invitation.query.filter_by(survey_id=survey_id)
	participant_ids = [i.participant_id for i in invitations]
	print (participant_ids)
	user_answers = UserAnswer.query.filter_by(survey_id=survey_id).order_by(UserAnswer.answer_id)
	correct_answers = Answer.query.filter_by(survey_id=survey_id).order_by(Answer.id)

	result = UserAnswer.query.join(Answer, UserAnswer.answer_id==Answer.id).filter(UserAnswer.survey_id==survey_id).add_entity(Answer.is_correct)

	#for r in result:
	#	print(r[0].__dict__, r[1])

	# {id: [#False, #True]}
	#d = {correct_answers[i].id: [0, 0] for i in range(correct_answers.count())}

	# {id: [#False, #True]}
	d_questions = {questions[i].id: [0, 0] for i in range(questions.count())}
	
	#for r in result:
	#	if r[0].is_correct == r[1]:
	#		d[r[0].answer_id][1] = d[r[0].answer_id][1] + 1
	#	else:
	#		d[r[0].answer_id][0] = d[r[0].answer_id][0] + 1


	for p_id in participant_ids:
		for q in questions:
			question_is_correct = True
			for r in result:
				if p_id == r[0].user_id and q.id == r[0].question_id:
					if r[0].is_correct != r[1]:
						question_is_correct = False
			if question_is_correct:
				d_questions[q.id][1] = d_questions[q.id][1] + 1
			else:
				d_questions[q.id][0] = d_questions[q.id][0] + 1

	results = []
	for key, value in d_questions.items():
		results.append(value)

	return results

@app.route('/plot.png/<survey_id>')
def plot_png(survey_id):
	ys = get_results_of(survey_id)

	fig = create_figure(ys)
	output = io.BytesIO()
	FigureCanvas(fig).print_png(output)

	return Response(output.getvalue(), mimetype='image/png')

def create_figure(input_ys):
	fig = Figure()
	axis = fig.add_subplot(1, 1, 1)
	xs_cor = []
	xs_inc = []
	xs = []
	ys = []
	w = 0.1
	correct = []
	incorrect = []
	for i in range(len(input_ys)):
		xs.append(i+1)
		xs_cor.append(i+1-w)
		xs_inc.append(i+1+w)
		correct.append(input_ys[i][1])
		incorrect.append(input_ys[i][0])
	xs.append(len(input_ys))
	for i in range(correct[0]+incorrect[0]):
		ys.append(i)
	ys.append(len(input_ys))

	print (correct, incorrect)
	axis.bar(xs_cor, correct, width=0.2, color='#cafcb6', align='center', label='correct')
	axis.bar(xs_inc, incorrect, width=0.2, color='#ffa4a1', align='center', label='incorrect')

	axis.set_xticks(xs)
	axis.set_yticks(ys)
	axis.set_xlabel('Answer')
	axis.set_ylabel('Participants')
	axis.plot()

	axis.legend(loc="best")
	return fig


@app.route('/newSurvey')
@login_required
def newSurvey():
	return render_template('newSurvey.html')


@app.route('/editSurvey/<survey_id>', methods=['GET', 'POST'])
@login_required
def editSurvey(survey_id):
	survey = Survey.query.get(survey_id)
	questions = Question.query.filter_by(survey_id=survey.id)
	answers = Answer.query.filter_by(survey_id=survey.id)

	return render_template('editSurvey.html', survey=survey, questions=questions, answers=answers)


@app.route('/joinSurvey/<invitation_id>', methods=['GET', 'POST'])
def joinSurvey(invitation_id):
	invitation = Invitation.query.get(invitation_id)
	survey = Survey.query.get(invitation.survey_id)
	questions = Question.query.filter_by(survey_id=invitation.survey_id)
	answers = Answer.query.filter_by(survey_id=invitation.survey_id)

	is_available = False
	if survey.start_time <= datetime.now() <= survey.end_time:
		is_available = True
	else:
		is_available = False
		survey.status = False

	db.session.commit()

	return render_template('joinSurvey.html', survey=survey, questions=questions, answers=answers, is_available=is_available)


@app.route("/startSurvey", methods=['GET', 'POST'])
@login_required
def startSurvey():
	survey_id = request.form['survey_id']
	survey = Survey.query.get(survey_id)
	start_time = datetime.strptime(request.form['startTime'], '%Y-%m-%dT%H:%M')
	end_time = datetime.strptime(request.form['endTime'], '%Y-%m-%dT%H:%M')

	if start_time < end_time:
		print ("inside of if")
		survey.start_time = start_time
		survey.end_time = end_time
		survey.status = True
		db.session.commit()
	else:
		print('Start_time >= end_time!', survey_id)

	return redirect(url_for('survey', survey_id=survey_id))


@app.route('/stopSurvey', methods=['GET', 'POST'])
def stopSurvey():
	survey_id = request.form['survey_id']
	survey = Survey.query.get(survey_id)
	survey.status = False
	db.session.commit()

	return redirect(url_for('survey', survey_id=survey_id))


@app.route('/answerSurvey', methods=['GET', 'POST'])
@login_required
def answerSurvey():
	answers_user = request.form.getlist('answers')
	answers_correct = Answer.query.filter(Answer.id.in_(request.form.getlist('answer_ids'))).all()

	for i in range(len(answers_user)-1, -1, -1):
		if answers_user[i] == '1':
			answers_user[i] = True
			del answers_user[i + 1]
		else:
			answers_user[i] = False

	d = {answers_correct[i].id: [answers_correct[i].question_id, answers_user[i]] for i in range(len(answers_user))}

	for key, value in d.items():
		new_user_answer = UserAnswer(user_id=current_user.id, survey_id=answers_correct[0].survey_id, answer_id=key, question_id=value[0], is_correct=value[1])
		db.session.add(new_user_answer)
		print(key, value)

	db.session.commit()

	return redirect(url_for('dashboard'))


@app.route('/createSurvey', methods=['POST'])
@login_required
def createSurvey():
	title = request.form['surveyName']
	body = request.form['surveyDesc']
	survey_status = False

	signature = Survey(title=title, body=body, admin_id=current_user.id, status=survey_status)
	db.session.add(signature)
	db.session.commit()

	return redirect(url_for('editSurvey', survey_id=signature.id))


@app.route('/createQuestion', methods=['POST'])
@login_required
def createQuestion():
	body = request.form['questionBody']
	survey_id = request.form['questionSurveyId']

	signature = Question(body=body, survey_id=survey_id)
	db.session.add(signature)
	db.session.commit()

	fir_a_body = request.form['firstAnswer']
	fir_a_check = False
	if request.form.get('checkFirst') == 'on':
		fir_a_check = True
	if fir_a_body:
		sign_fir_a = Answer(body=fir_a_body, question_id=signature.id, survey_id=survey_id, is_correct=fir_a_check)
		db.session.add(sign_fir_a)

	sec_a_body = request.form['secondAnswer']
	sec_a_check = False
	if request.form.get('checkSecond') == 'on':
		sec_a_check = True
	if sec_a_body:
		sign_sec_a = Answer(body=sec_a_body, question_id=signature.id, survey_id=survey_id, is_correct=sec_a_check)
		db.session.add(sign_sec_a)

	thi_a_body = request.form['thirdAnswer']
	thi_a_check = False
	if request.form.get('checkThird') == 'on':
		thi_a_check = True
	if thi_a_body:
		sign_thi_a = Answer(body=thi_a_body, question_id=signature.id, survey_id=survey_id, is_correct=thi_a_check)
		db.session.add(sign_thi_a)

	fou_a_body = request.form['fourthAnswer']
	fou_a_check = False
	if request.form.get('checkFourth') == 'on':
		fou_a_check = True
	#fou_a_check = request.form.get('checkFourth')
	if fou_a_body:
		sign_fou_a = Answer(body=fou_a_body, question_id=signature.id, survey_id=survey_id, is_correct=fou_a_check)
		db.session.add(sign_fou_a)

	db.session.commit()

	return redirect(url_for('editSurvey', survey_id=survey_id))


# @TODO:
#   1. Flag status (survey->schema.sql)
#      - kann über survey admin geändert werden, wenn gedrückt, dann 0, 1 wenn active
#      - wenn timeframe abgelaufen, dann status->0
#   2. (not possible) Drop down start/end time für firefox
#   3. invite users form schöner
#   4. (Done) popup, wenn starttime > endtime
@app.route('/sendInvite', methods=['GET', 'POST'])
@login_required
def sendInvite():
	users = request.form.getlist('users')
	survey_id = request.form['surveyId']

	participants = User.query.filter(User.id.in_(users)).all()
	survey = Survey.query.get(survey_id)

	for p in participants:
		signature = Invitation(admin_id=current_user.id, admin_username=current_user.username, participant_id=p.id, survey_id=survey.id)
		db.session.add(signature)
	db.session.commit()

	return redirect(url_for('survey', survey_id=survey_id))


# ---------------------------- TOKEN -------------------------- #
@app.route('/createToken', methods=['GET', 'POST'])
@login_required
def createToken():
	survey_id = request.form['survey_id']
	available = request.form['available']
	#token_key = get_random_string(8)
	token_key = str(uuid4())
	used = 0
	
	token = Token(token_key=token_key, used=used, available=available, survey_id=survey_id)
	db.session.add(token)
	db.session.commit()

	return redirect(url_for('survey', survey_id=survey_id))

def get_random_string(length):
	letters = string.ascii_lowercase
	result_str = ''.join(random.choice(letters) for i in range(length))
	return result_str

if __name__ == '__main__':
	app.run(port=8000, debug=True)





# ---------------------------- Information ----------------------------
# How to change port? (do on restart)
# - in command line: export FLASK_RUN_PORT=8000
# - see: https://www.youtube.com/watch?v=MJ6KHXZH2YQ