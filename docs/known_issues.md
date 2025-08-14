# Known Issues

This document lists the known issues with the GoLink backend development environment.

## `rides` App Test Discovery Issue

**Date:** 2025-08-13

**Description:**
The test runner (`pytest` and Django's built-in test runner) is unable to discover and run the tests for the `rides` app. This issue seems to be specific to the development environment and is likely caused by a problem with the Python path configuration.

**Symptoms:**
-   When running `pytest rides/` or `python manage.py test rides`, the test runner reports that it has found 0 tests.
-   Running the tests with absolute paths or by manipulating `sys.path` results in `ImportError: attempted relative import with no known parent package`.

**Attempts to Resolve:**
The following steps have been taken to try to resolve this issue, without success:
-   Using absolute paths for the test files.
-   Setting the `DJANGO_SETTINGS_MODULE` and `PYTHONPATH` environment variables.
-   Running `pytest` from the project root.
-   Renaming the test file.
-   Ensuring the `rides` app directory is a proper Python package with an `__init__.py` file.

**Status:**
The tests for the `rides` app are written and are located in `backend/rides/tests.py`. They are believed to be correct and should run in a standard Django and pytest environment. However, they cannot be verified in the current development environment.

**Next Steps:**
This issue will be revisited during the backend finalization phase. For now, development will proceed with the understanding that the tests for the `rides` app are written but not running.
