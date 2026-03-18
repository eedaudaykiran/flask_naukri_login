import pkgutil
import importlib.util

# Python 3.12+ compatibility patch (get_loader removed in 3.12)
if not hasattr(pkgutil, "get_loader"):
    def get_loader(name):
        try:
            spec = importlib.util.find_spec(name)
        except ValueError:
            # Handle special cases like __main__ where find_spec fails
            return None
        return spec.loader if spec else None
    pkgutil.get_loader = get_loader

from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
from sqlalchemy import inspect, text

from config import Config
from models import db, User, JobSeekerProfile, RecruiterProfile, Job, JobApplication, OTPVerification, BlockedCompany
from forms import (
    RegistrationForm, LoginForm, JobSeekerProfileForm, ResumeUploadForm,
    PhotoUploadForm, PostJobForm, ChangePasswordForm, ForgotPasswordForm,
    OTPVerificationForm, ResetPasswordForm, BlockCompanyForm
)
from utils import (
    generate_otp, validate_password_strength,
    send_otp_email, send_otp_sms,
    save_uploaded_file, get_profile_visibility_message,
    check_password_expiry_notification
)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'resumes'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'kyc'), exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

    # DB schema migration: add missing columns if user already had old table
    inspector = inspect(db.engine)
    if 'users' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'phone' not in columns:
            db.session.execute(text('ALTER TABLE users ADD COLUMN phone VARCHAR(15)'))
            db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered. Please use a different email.', 'danger')
            return render_template('register.html', form=form)
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken. Please choose another.', 'danger')
            return render_template('register.html', form=form)

        is_valid, message = validate_password_strength(form.password.data)
        if not is_valid:
            flash(f'Password requirements not met: {message}', 'danger')
            return render_template('register.html', form=form)

        user = User(email=form.email.data, phone=form.phone.data, username=form.username.data, user_type=form.user_type.data, is_verified=True)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'verification_user_id' not in session:
        flash('No pending verification found.', 'warning')
        return redirect(url_for('register'))

    # OTP check removed: registration is now instant verified.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter((User.username == form.username.data) | (User.email == form.username.data)).first()
        if user:
            if user.locked_until and user.locked_until > datetime.utcnow():
                minutes_left = (user.locked_until - datetime.utcnow()).seconds // 60
                flash(f'Account locked due to too many failed attempts. Try again in {minutes_left} minutes.', 'danger')
                return render_template('login.html', form=form)

            if user.check_password(form.password.data):
                # OTP verification step removed as user is marked verified on signup
                if user.check_password_expired():
                    flash('Your password has expired. Please change it to continue.', 'warning')
                    return redirect(url_for('change_password'))

                user.reset_login_attempts()
                login_user(user, remember=form.remember.data)
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                user.increment_login_attempts()
                flash('Invalid password. Please try again.', 'danger')
        else:
            flash('User not found. Please check your credentials.', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            otp = generate_otp()
            otp_record = OTPVerification(user_id=user.id, otp=otp, purpose='password_reset', expires_at=datetime.utcnow() + timedelta(minutes=10))
            db.session.add(otp_record)
            db.session.commit()
            session['reset_user_id'] = user.id
            flash(f'OTP sent to your email. Your OTP is: {otp} (In production, this would be sent via email)', 'info')
            return redirect(url_for('reset_password'))
        else:
            flash('Email not found in our records.', 'danger')
    return render_template('forgot_password.html', form=form)

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_user_id' not in session:
        flash('No password reset request found.', 'warning')
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.get(session['reset_user_id'])
        if not user.can_use_password(form.new_password.data):
            flash('You cannot reuse your last password. Please choose a different one.', 'danger')
            return render_template('reset_password.html', form=form)

        is_valid, message = validate_password_strength(form.new_password.data)
        if not is_valid:
            flash(f'Password requirements not met: {message}', 'danger')
            return render_template('reset_password.html', form=form)

        user.set_password(form.new_password.data)
        db.session.commit()
        session.pop('reset_user_id')
        flash('Password reset successful! Please log in with your new password.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    password_status = check_password_expiry_notification(current_user)
    if password_status.get('expired'):
        flash(password_status['message'], 'warning')
        return redirect(url_for('change_password'))
    elif password_status.get('expires_soon'):
        flash(password_status['message'], 'info')

    if current_user.user_type == 'jobseeker':
        profile = JobSeekerProfile.query.filter_by(user_id=current_user.id).first()
        if profile:
            applications = JobApplication.query.filter_by(jobseeker_id=profile.id).all()
            return render_template('jobseeker_dashboard.html', profile=profile, applications=applications)
        else:
            return redirect(url_for('create_profile'))
    else:
        profile = RecruiterProfile.query.filter_by(user_id=current_user.id).first()
        if profile:
            jobs = Job.query.filter_by(recruiter_id=profile.id).all()
            return render_template('recruiter_dashboard.html', profile=profile, jobs=jobs)
        else:
            return redirect(url_for('create_recruiter_profile'))

@app.route('/create-profile', methods=['GET', 'POST'])
@login_required
def create_profile():
    if current_user.user_type != 'jobseeker':
        flash('Invalid access.', 'danger')
        return redirect(url_for('dashboard'))

    existing_profile = JobSeekerProfile.query.filter_by(user_id=current_user.id).first()
    if existing_profile:
        return redirect(url_for('dashboard'))

    form = JobSeekerProfileForm()
    if form.validate_on_submit():
        if form.is_fresher.data:
            current_employer = 'Not Applicable'
            current_designation = 'Not Applicable'
        else:
            current_employer = form.current_employer.data
            current_designation = form.current_designation.data

        profile = JobSeekerProfile(
            user_id=current_user.id,
            full_name=form.full_name.data,
            phone=form.phone.data,
            date_of_birth=form.date_of_birth.data,
            gender=form.gender.data,
            is_fresher=form.is_fresher.data,
            current_employer=current_employer,
            current_designation=current_designation,
            highest_qualification=form.highest_qualification.data,
            college_name=form.college_name.data,
            graduation_year=form.graduation_year.data,
            specialization=form.specialization.data,
            key_skills=form.key_skills.data,
            profile_visibility=form.profile_visibility.data
        )

        profile.profile_completion_percentage = profile.calculate_completion_percentage()
        db.session.add(profile)
        db.session.commit()

        flash('Profile created successfully! Complete your profile by adding a photo and resume.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_profile.html', form=form)

@app.route('/upload-resume', methods=['GET', 'POST'])
@login_required
def upload_resume():
    if current_user.user_type != 'jobseeker':
        flash('Invalid access.', 'danger')
        return redirect(url_for('dashboard'))

    profile = JobSeekerProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('create_profile'))

    form = ResumeUploadForm()
    if form.validate_on_submit():
        file = form.resume.data
        file_path, filename = save_uploaded_file(file, app.config['UPLOAD_FOLDER'], 'resumes')
        if file_path:
            profile.resume_path = file_path
            profile.resume_filename = filename
            profile.resume_uploaded_at = datetime.utcnow()
            profile.profile_completion_percentage = profile.calculate_completion_percentage()
            db.session.commit()
            flash('Resume uploaded successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Error uploading file. Please try again.', 'danger')

    return render_template('upload_resume.html', form=form)

@app.route('/upload-photo', methods=['GET', 'POST'])
@login_required
def upload_photo():
    if current_user.user_type != 'jobseeker':
        flash('Invalid access.', 'danger')
        return redirect(url_for('dashboard'))

    profile = JobSeekerProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('create_profile'))

    form = PhotoUploadForm()
    if form.validate_on_submit():
        file = form.photo.data
        file_path, filename = save_uploaded_file(file, app.config['UPLOAD_FOLDER'], 'photos')
        if file_path:
            profile.photo = file_path
            profile.profile_completion_percentage = profile.calculate_completion_percentage()
            db.session.commit()
            flash('Photo uploaded successfully! You are now 40% more likely to get contacted!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Error uploading photo. Please try again.', 'danger')

    return render_template('upload_photo.html', form=form)

@app.route('/profile/<int:user_id>')
@login_required
def view_profile(user_id):
    profile = JobSeekerProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        flash('Profile not found.', 'danger')
        return redirect(url_for('index'))

    if current_user.user_type == 'recruiter':
        if profile.profile_visibility == 'hidden':
            flash('This profile is hidden.', 'danger')
            return redirect(url_for('dashboard'))
        elif profile.profile_visibility == 'visible_with_exceptions':
            blocked = BlockedCompany.query.filter_by(jobseeker_id=profile.id, company_name=current_user.recruiter_profile.company_name).first()
            if blocked:
                flash('You cannot view this profile (blocked by user).', 'danger')
                return redirect(url_for('dashboard'))

    return render_template('view_profile.html', profile=profile)

@app.route('/block-company', methods=['GET', 'POST'])
@login_required
def block_company():
    if current_user.user_type != 'jobseeker':
        flash('Invalid access.', 'danger')
        return redirect(url_for('dashboard'))

    profile = JobSeekerProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('create_profile'))

    form = BlockCompanyForm()
    if form.validate_on_submit():
        blocked = BlockedCompany(jobseeker_id=profile.id, company_name=form.company_name.data)
        db.session.add(blocked)
        profile.profile_visibility = 'visible_with_exceptions'
        db.session.commit()
        flash(f'Company "{form.company_name.data}" blocked successfully!', 'success')
        return redirect(url_for('dashboard'))

    blocked_companies = BlockedCompany.query.filter_by(jobseeker_id=profile.id).all()
    return render_template('block_company.html', form=form, blocked_companies=blocked_companies)

@app.route('/search-jobs')
@login_required
def search_jobs():
    keyword = request.args.get('keyword', '')
    location = request.args.get('location', '')
    query = Job.query.filter_by(is_active=True)
    if keyword:
        query = query.filter(Job.title.contains(keyword) | Job.description.contains(keyword))
    if location:
        query = query.filter(Job.location.contains(location))
    jobs = query.order_by(Job.is_featured.desc(), Job.created_at.desc()).all()
    return render_template('search_jobs.html', jobs=jobs, keyword=keyword, location=location)

@app.route('/apply-job/<int:job_id>')
@login_required
def apply_job(job_id):
    if current_user.user_type != 'jobseeker':
        flash('Only job seekers can apply for jobs.', 'danger')
        return redirect(url_for('dashboard'))

    job = Job.query.get_or_404(job_id)
    profile = JobSeekerProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Please complete your profile before applying.', 'warning')
        return redirect(url_for('create_profile'))

    existing = JobApplication.query.filter_by(job_id=job_id, jobseeker_id=profile.id).first()
    if existing:
        flash('You have already applied for this job.', 'info')
        return redirect(url_for('view_job', job_id=job_id))

    application = JobApplication(job_id=job_id, jobseeker_id=profile.id)
    db.session.add(application)
    db.session.commit()
    flash('Application submitted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/job/<int:job_id>')
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template('view_job.html', job=job)

@app.route('/create-recruiter-profile', methods=['GET', 'POST'])
@login_required
def create_recruiter_profile():
    if current_user.user_type != 'recruiter':
        flash('Invalid access.', 'danger')
        return redirect(url_for('dashboard'))

    existing = RecruiterProfile.query.filter_by(user_id=current_user.id).first()
    if existing:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        profile = RecruiterProfile(
            user_id=current_user.id,
            company_name=request.form.get('company_name'),
            company_email=request.form.get('company_email'),
            company_phone=request.form.get('company_phone'),
            company_address=request.form.get('company_address'),
            company_website=request.form.get('company_website'),
            recruiter_name=request.form.get('recruiter_name'),
            designation=request.form.get('designation'),
            pan_number=request.form.get('pan_number')
        )
        db.session.add(profile)
        db.session.commit()
        flash('Recruiter profile created. Please complete KYC verification.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_recruiter_profile.html')

@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    if current_user.user_type != 'recruiter':
        flash('Only recruiters can post jobs.', 'danger')
        return redirect(url_for('dashboard'))

    profile = RecruiterProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('create_recruiter_profile'))

    form = PostJobForm()
    if form.validate_on_submit():
        expires_at = datetime.utcnow() + timedelta(days=30)
        job = Job(
            recruiter_id=profile.id,
            title=form.title.data,
            description=form.description.data,
            requirements=form.requirements.data,
            location=form.location.data,
            salary_min=form.salary_min.data,
            salary_max=form.salary_max.data,
            experience_required=form.experience_required.data,
            job_type=form.job_type.data,
            is_featured=form.is_featured.data,
            expires_at=expires_at
        )
        db.session.add(job)
        db.session.commit()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('post_job.html', form=form)

@app.route('/view-applicants/<int:job_id>')
@login_required
def view_applicants(job_id):
    if current_user.user_type != 'recruiter':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    job = Job.query.get_or_404(job_id)
    if job.recruiter.user_id != current_user.id:
        flash('You do not have permission to view these applicants.', 'danger')
        return redirect(url_for('dashboard'))

    applications = job.applications.all()
    return render_template('view_applicants.html', job=job, applications=applications)

@app.route('/update-application/<int:app_id>/<string:status>')
@login_required
def update_application(app_id, status):
    if current_user.user_type != 'recruiter':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    application = JobApplication.query.get_or_404(app_id)
    if application.job.recruiter.user_id != current_user.id:
        flash('You do not have permission to update this application.', 'danger')
        return redirect(url_for('dashboard'))

    application.status = status
    if status in ['shortlisted', 'rejected']:
        application.viewed_at = datetime.utcnow()
    db.session.commit()
    flash(f'Application {status} successfully!', 'success')
    return redirect(url_for('view_applicants', job_id=application.job_id))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('change_password.html', form=form)

        if not current_user.can_use_password(form.new_password.data):
            flash('You cannot reuse your last password. Please choose a different one.', 'danger')
            return render_template('change_password.html', form=form)

        is_valid, message = validate_password_strength(form.new_password.data)
        if not is_valid:
            flash(f'Password requirements not met: {message}', 'danger')
            return render_template('change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('change_password.html', form=form)

@app.route('/profile-visibility/<string:visibility>')
@login_required
def set_visibility(visibility):
    if current_user.user_type != 'jobseeker':
        flash('Invalid access.', 'danger')
        return redirect(url_for('dashboard'))

    if visibility not in ['visible', 'hidden', 'visible_with_exceptions']:
        flash('Invalid visibility setting.', 'danger')
        return redirect(url_for('dashboard'))

    profile = JobSeekerProfile.query.filter_by(user_id=current_user.id).first()
    if profile:
        profile.profile_visibility = visibility
        db.session.commit()
        message = get_profile_visibility_message(visibility, bool(profile.photo))
        flash(message, 'success')

    return redirect(url_for('dashboard'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)