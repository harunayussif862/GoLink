# GoLink Backend Test Guidelines

This document provides guidelines for writing tests for the GoLink backend, especially for features that involve complex data structures and file uploads.

## General Principles

-   **Test Isolation:** Tests should be independent of each other. Do not rely on the state created by other tests. Use `setUp` or `setUpTestData` to create the necessary objects for each test or test class.
-   **Clean Test Data:** Use unique data for each test to avoid conflicts (e.g., unique usernames, emails).
-   **Test-Driven Development (TDD):** Whenever possible, write a failing test first, then write the code to make it pass.

## Testing Role Applications with Dynamic Forms

The role application system uses a dynamic form structure with `RoleForm`, `FormField`, and `RoleApplication` models. Here's how to test it:

### Creating a Role Application in a Test

When testing the creation of a `RoleApplication`, you need to simulate a `multipart/form-data` request that includes both JSON data for the form fields and the actual files.

**Key points:**

-   The non-file form data should be sent as a JSON string in a field named `form_data`.
-   The files should be sent as separate parts of the multipart request. The name of each file part should match the `label` of the corresponding `FormField`.

**Example:**

```python
import json
from django.urls import reverse
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import RoleForm, FormField

class RoleApplicationAPITests(APITestCase):

    def setUp(self):
        # ... create user, role_form, etc. ...
        self.apply_url = reverse('accounts:role_apply')

    def test_apply_for_role(self):
        document = SimpleUploadedFile("license.txt", b"file_content", content_type="text/plain")
        form_data = {
            'License Number': '12345',
        }
        data = {
            'role_form': self.role_form.id,
            'form_data': json.dumps(form_data),
            'License Document': document  # The key here matches the FormField label
        }
        response = self.client.post(self.apply_url, data, format='multipart')
        # ... assertions ...
```

### Backend View Logic

The `RoleApplicationView` on the backend is responsible for parsing this custom multipart request. It does the following:

1.  It expects the `form_data` field to be a JSON string and parses it into a Python dictionary.
2.  It iterates through `request.FILES` and adds each file to a new `RoleApplicationFile` model instance, linking it to the `RoleApplication`.

This approach allows for a flexible and extensible way to handle dynamic forms with file uploads.
