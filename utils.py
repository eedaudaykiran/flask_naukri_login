import os
import random
import string
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import re

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    # Placeholder / demo OTP email send
    print(f"[OTP EMAIL] to {email}: Your OTP is {otp}")
    return True

def send_otp_sms(phone, otp):
    # Placeholder / demo OTP SMS send
    print(f"[OTP SMS] to {phone}: Your OTP is {otp}")
    return True

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def validate_password_strength(password):
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is strong"

def calculate_profile_completion(profile_data):
    required_fields = [
        'full_name', 'phone', 'highest_qualification',
        'college_name', 'graduation_year', 'specialization', 'key_skills'
    ]
    optional_fields = ['date_of_birth', 'gender', 'photo']
    filled_required = sum(1 for field in required_fields if profile_data.get(field))
    filled_optional = sum(1 for field in optional_fields if profile_data.get(field))
    required_percentage = (filled_required / len(required_fields)) * 70 if required_fields else 0
    optional_percentage = (filled_optional / len(optional_fields)) * 30 if optional_fields else 0
    total_percentage = required_percentage + optional_percentage
    if profile_data.get('photo'):
        total_percentage = min(100, total_percentage + 10)
    missing_fields = [field for field in required_fields if not profile_data.get(field)]
    return int(total_percentage), missing_fields

def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def save_uploaded_file(file, upload_folder, subfolder=''):
    if file:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        new_filename = f"{name}_{timestamp}{ext}"
        save_path = os.path.join(upload_folder, subfolder)
        os.makedirs(save_path, exist_ok=True)
        full_path = os.path.join(save_path, new_filename)
        file.save(full_path)
        rel_path = os.path.join(subfolder, new_filename)
        return rel_path, new_filename
    return None, None

def parse_skills(skills_string):
    if not skills_string:
        return []
    return [skill.strip() for skill in skills_string.split(',') if skill.strip()]

def format_skills(skills_list):
    if not skills_list:
        return ''
    return ', '.join(skills_list)

def get_profile_visibility_message(visibility, has_photo=False):
    messages = {
        'visible': "Your profile is visible to all recruiters",
        'hidden': "Your profile is hidden. Recruiters cannot find you",
        'visible_with_exceptions': "Your profile is visible except to blocked companies"
    }
    base_message = messages.get(visibility, "Profile visibility setting active")
    if has_photo:
        base_message += " - You're 40% more likely to get contacted with a photo!"
    return base_message

def validate_recruiter_kyc(pan_number, address_proof_file):
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    if pan_number and re.match(pan_pattern, pan_number):
        return True, "KYC documents validated"
    else:
        return False, "Invalid PAN card format"

def check_password_expiry_notification(user):
    if user.last_password_change:
        days_until_expiry = 30 - (datetime.utcnow() - user.last_password_change).days
        if 0 < days_until_expiry <= 2:
            return {'expires_soon': True, 'days_left': days_until_expiry, 'message': f"Your password will expire in {days_until_expiry} days. Please change it."}
        elif days_until_expiry <= 0:
            return {'expired': True, 'message': "Your password has expired. Please change it to continue."}
    return {'expires_soon': False}
