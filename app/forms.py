from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, SubmitField
from wtforms.validators import DataRequired, Email

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class SignupForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    profile_picture = FileField('Profile Picture')
    submit = SubmitField('Sign Up')

class DeleteAccountForm(FlaskForm):
    submit = SubmitField('Delete Account')

class FeedbackForm(FlaskForm):
    feedback = StringField('Feedback', validators=[DataRequired()])  
    submit = SubmitField('Submit Feedback')
