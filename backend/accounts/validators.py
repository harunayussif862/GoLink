from django.core.exceptions import ValidationError
import os

def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.pdf', '.jpg', '.png', '.jpeg']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension. Only PDF, JPG, and PNG are allowed.')

def validate_file_size(value):
    filesize = value.size
    if filesize > 5 * 1024 * 1024: # 5MB
        raise ValidationError("The maximum file size that can be uploaded is 5MB.")
    else:
        return value
