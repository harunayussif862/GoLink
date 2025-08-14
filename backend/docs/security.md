# Security Documentation

This document outlines security-related features and configurations for the GoLink platform.

## Password Management

### Change Password Endpoint

A secure endpoint is provided for users to change their password.

**Endpoint:** `POST /api/auth/change-password/`

**Authentication:** Requires a valid user authentication token.

**Request Body:**

| Field           | Type   | Description                                                                 |
|-----------------|--------|-----------------------------------------------------------------------------|
| `old_password`  | string | The user's current password.                                                |
| `new_password1` | string | The user's desired new password.                                            |
| `new_password2` | string | Confirmation of the new password. Must match `new_password1`.               |
| `otp_code`      | string | A valid 6-digit OTP code from the user's authenticator app. **Required if the user has 2FA enabled.** |

**Behavior:**

1.  **Authorization:** The user must be authenticated.
2.  **Old Password Verification:** The provided `old_password` is checked against the user's current password.
3.  **2FA Verification:** If the user has 2FA enabled on their account, the `otp_code` is required and will be validated. If 2FA is not enabled, this field is ignored.
4.  **New Password Validation:** The `new_password1` is validated against Django's password validators to ensure it meets complexity requirements.
5.  **Token Revocation:** Upon a successful password change, **all** of the user's active authentication tokens (Knox tokens) are immediately revoked. This means the user will be logged out of all other sessions for security.
6.  **Email Notification:** A notification email is sent to the user's registered email address, alerting them that their password has been changed. The email includes the timestamp (UTC) and the IP address from which the request originated.
7.  **Rate Limiting:** This endpoint is rate-limited to **5 attempts per user per hour** to protect against brute-force attacks. Exceeding this limit will result in a `429 Too Many Requests` error.
8.  **Logging:** Every successful password change is logged as a security-audit event, including the user ID, timestamp, and IP address.
