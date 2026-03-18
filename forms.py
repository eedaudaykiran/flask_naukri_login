from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, PasswordField, SelectField, TextAreaField, DateField, IntegerField, BooleanField, RadioField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional, NumberRange
import re
from datetime import date

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])
    phone = StringField('Mobile Number', validators=[
        DataRequired(message="Mobile number is required"),
        Length(min=10, max=15, message="Please enter a valid mobile number")
    ])
    username = StringField('Username', validators=[
        DataRequired(message="Username is required"),
        Length(min=4, max=80, message="Username must be between 4 and 80 characters")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=6, message="Password must be at least 6 characters long (Naukri policy)")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ])
    user_type = RadioField('I am a', choices=[
        ('jobseeker', 'Job Seeker'),
        ('recruiter', 'Recruiter')
    ], validators=[DataRequired()])

    def validate_password(self, field):
        password = field.data
        if self.username.data and self.username.data.lower() in password.lower():
            raise ValidationError("Password cannot contain your username")
        if self.email.data:
            email_prefix = self.email.data.split('@')[0].lower()
            if email_prefix in password.lower():
                raise ValidationError("Password cannot contain your email address")
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password should contain at least one number (recommended)")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password should contain at least one special character (recommended)")
        if not (re.search(r'[A-Z]', password) and re.search(r'[a-z]', password)):
            raise ValidationError("Password should contain both uppercase and lowercase letters (Naukri is case-sensitive)")

class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[
        DataRequired(message="Username or email is required")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required")
    ])
    remember = BooleanField('Remember Me')

class JobSeekerProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(message="Full name is required")])
    phone = StringField('Mobile Number', validators=[
        DataRequired(message="Mobile number is required"),
        Length(min=10, max=15, message="Please enter a valid mobile number")
    ])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()])
    gender = SelectField('Gender', choices=[('', 'Select Gender'), ('male', 'Male'), ('female', 'Female'), ('other', 'Other')], validators=[Optional()])
    is_fresher = BooleanField('I am a Fresher')
    current_employer = StringField('Current Employer', validators=[Optional()])
    current_designation = StringField('Current Designation', validators=[Optional()])
    highest_qualification = StringField('Highest Qualification', validators=[DataRequired(message="Highest qualification is required")])
    college_name = StringField('College/University Name', validators=[DataRequired(message="College name is required")])
    graduation_year = IntegerField('Year of Graduation', validators=[
        DataRequired(message="Graduation year is required"),
        NumberRange(min=1950, max=date.today().year, message="Please enter a valid year")
    ])
    specialization = StringField('Specialization', validators=[DataRequired(message="Specialization is required")])
    key_skills = StringField('Key Skills (comma-separated)', validators=[DataRequired(message="Key skills are required - recruiters search for these!")])
    profile_visibility = SelectField('Profile Visibility', choices=[
        ('visible', 'Visible to all recruiters'),
        ('hidden', 'Hidden (invisible to recruiters)'),
        ('visible_with_exceptions', 'Visible except blocked companies')
    ], validators=[DataRequired()])

    def validate_current_employer(self, field):
        if self.is_fresher.data and field.data and field.data.lower() != 'not applicable':
            field.data = 'Not Applicable'

    def validate_current_designation(self, field):
        if self.is_fresher.data and field.data and field.data.lower() != 'not applicable':
            field.data = 'Not Applicable'

class ResumeUploadForm(FlaskForm):
    resume = FileField('Upload Resume', validators=[
        DataRequired(message="Please select a file to upload"),
        FileAllowed(['pdf', 'doc', 'docx', 'rtf'], 'Only PDF, DOC, DOCX, and RTF files are allowed!'),
        FileSize(max_size=2 * 1024 * 1024, message="File size must be less than 2MB")
    ])

class PhotoUploadForm(FlaskForm):
    photo = FileField('Upload Photo', validators=[
        DataRequired(message="Please select a photo"),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Only JPG, JPEG, and PNG files are allowed!'),
        FileSize(max_size=1 * 1024 * 1024, message="Photo size must be less than 1MB")
    ])

class PostJobForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired(message="Job title is required")])
    description = TextAreaField('Job Description', validators=[DataRequired(message="Job description is required")])
    requirements = TextAreaField('Requirements', validators=[DataRequired(message="Requirements are required")])
    location = StringField('Location', validators=[DataRequired(message="Location is required")])
    salary_min = IntegerField('Minimum Salary (per year)', validators=[Optional()])
    salary_max = IntegerField('Maximum Salary (per year)', validators=[Optional()])
    experience_required = StringField('Experience Required', validators=[DataRequired(message="Experience required is needed")])
    job_type = SelectField('Job Type', choices=[('full-time', 'Full Time'), ('part-time', 'Part Time'), ('contract', 'Contract'), ('internship', 'Internship')], validators=[DataRequired()])
    is_featured = BooleanField('Feature this job (sponsored)')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired(message="Current password is required")])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required"),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_new_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your new password"),
        EqualTo('new_password', message="Passwords must match")
    ])

    def validate_new_password(self, field):
        password = field.data
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password should contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password should contain at least one special character")
        if not (re.search(r'[A-Z]', password) and re.search(r'[a-z]', password)):
            raise ValidationError("Password should contain both uppercase and lowercase letters")

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])

class OTPVerificationForm(FlaskForm):
    otp = StringField('Enter OTP', validators=[
        DataRequired(message="OTP is required"),
        Length(min=6, max=6, message="OTP must be 6 digits")
    ])

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required"),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    confirm_new_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your new password"),
        EqualTo('new_password', message="Passwords must match")
    ])

class BlockCompanyForm(FlaskForm):
    company_name = StringField('Company Name to Block', validators=[
        DataRequired(message="Company name is required")
    ])
