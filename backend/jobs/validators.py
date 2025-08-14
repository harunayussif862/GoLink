from django.core.exceptions import ValidationError
import os

def validate_file_extension_pdf(value):
    """
    Validates that the file has a .pdf extension.
    """
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension. Only PDF files are allowed.')

def validate_file_size_10mb(value):
    """
    Validates that the file size is not more than 10MB.
    """
    filesize = value.size
    if filesize > 10 * 1024 * 1024: # 10MB
        raise ValidationError("The maximum file size that can be uploaded is 10MB.")
    return value
