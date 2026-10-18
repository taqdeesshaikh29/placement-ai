from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError

from app.models import User


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[
        DataRequired(message="Please enter your name."),
        Length(min=2, max=100, message="Name must be 2-100 characters."),
    ])
    email = StringField("Email", validators=[
        DataRequired(message="Please enter your email."),
        Email(message="Enter a valid email address."),
        Length(max=255),
    ])
    password = PasswordField("Password", validators=[
        DataRequired(message="Please choose a password."),
        Length(min=8, max=128, message="Password must be at least 8 characters."),
        Regexp(r"(?=.*[A-Za-z])(?=.*\d)",
               message="Password must contain at least one letter and one number."),
    ])
    confirm_password = PasswordField("Confirm password", validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo("password", message="Passwords do not match."),
    ])
    submit = SubmitField("Create account")

    def validate_email(self, field):
        email = field.data.strip().lower()
        if User.query.filter_by(email=email).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[
        DataRequired(message="Please enter your email."),
        Email(message="Enter a valid email address."),
    ])
    password = PasswordField("Password", validators=[
        DataRequired(message="Please enter your password."),
    ])
    remember = BooleanField("Remember me")
    submit = SubmitField("Log in")
