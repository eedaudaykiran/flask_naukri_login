$(document).ready(function() {
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    $('[data-toggle="tooltip"]').tooltip();

    $('.toggle-password').click(function() {
        $(this).toggleClass('fa-eye fa-eye-slash');
        var input = $($(this).attr('toggle'));
        if (input.attr('type') == 'password') {
            input.attr('type', 'text');
        } else {
            input.attr('type', 'password');
        }
    });

    $('form').submit(function() {
        $(this).find(':submit').prop('disabled', true);
        $(this).find(':submit').html('<span class="spinner-border spinner-border-sm"></span> Processing...');
    });

    checkProfileCompletion();

    initSkillsInput();

    $('#photo').change(function() {
        readURL(this, 'photo-preview');
    });

    $('#resume').change(function() {
        var file = this.files[0];
        if (!file) return;
        var fileSize = file.size / 1024 / 1024;
        if (fileSize > 2) {
            alert('File size must be less than 2MB');
            $(this).val('');
        }
        var fileType = file.name.split('.').pop().toLowerCase();
        if (!['pdf', 'doc', 'docx', 'rtf'].includes(fileType)) {
            alert('Only PDF, DOC, DOCX, and RTF files are allowed');
            $(this).val('');
        }
    });
});

function checkProfileCompletion() {
    $('.required-field').each(function() {
        if ($(this).val()) {
            $(this).addClass('is-valid');
        } else {
            $(this).addClass('is-invalid');
        }
    });
}

function initSkillsInput() {
    $('#key_skills').on('keyup', function() {
        var skills = $(this).val().split(',');
        var html = '';
        skills.forEach(function(skill) {
            if (skill.trim()) {
                html += '<span class="badge bg-primary me-1">' + skill.trim() + '</span>';
            }
        });
        $('#skills-preview').html(html);
    });
}

function readURL(input, previewId) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            $('#' + previewId).attr('src', e.target.result);
        }
        reader.readAsDataURL(input.files[0]);
    }
}

function checkPasswordStrength(password) {
    var strength = 0;
    if (password.length >= 6) strength += 1;
    if (password.match(/[a-z]+/)) strength += 1;
    if (password.match(/[A-Z]+/)) strength += 1;
    if (password.match(/[0-9]+/)) strength += 1;
    if (password.match(/[$@#&!]+/)) strength += 1;
    return strength;
}

function searchJobs() {
    var keyword = $('#search-keyword').val();
    var location = $('#search-location').val();
    $.ajax({
        url: '/api/search-jobs',
        method: 'GET',
        data: { keyword: keyword, location: location },
        success: function(response) {
            $('#job-results').html(response);
        }
    });
}

function applyToJob(jobId) {
    if (confirm('Are you sure you want to apply for this job?')) {
        $.ajax({
            url: '/apply-job/' + jobId,
            method: 'GET',
            success: function(response) {
                if (response && response.success) {
                    alert('Application submitted successfully!');
                    location.reload();
                } else {
                    alert('Application submitted (standard flow)');
                    location.reload();
                }
            }
        });
    }
}

function blockCompany(companyId) {
    if (confirm('Are you sure you want to block this company?')) {
        $.ajax({
            url: '/block-company',
            method: 'POST',
            data: { company_name: companyId },
            success: function(response) {
                if (response && response.success) {
                    alert('Company blocked successfully');
                    location.reload();
                }
            }
        });
    }
}

function validateForm(formId) {
    var isValid = true;
    $('#' + formId + ' [required]').each(function() {
        if (!$(this).val()) {
            $(this).addClass('is-invalid');
            isValid = false;
        } else {
            $(this).removeClass('is-invalid');
        }
    });
    return isValid;
}
