# Requirements Document

## Introduction

This feature adds a user authentication system to the Candidate Practice Portal. It covers a login page and a registration page, allowing candidates to create accounts with a username (full name), email, and password, and to sign in with their credentials. Authenticated sessions are maintained via a JWT stored in the browser. Unauthenticated users are redirected to the login page; authenticated users are redirected away from auth pages to the dashboard.

## Glossary

- **Portal**: The Candidate Practice Portal Next.js frontend application.
- **Auth API**: The FastAPI backend authentication endpoints (`/api/v1/auth/...`).
- **JWT**: JSON Web Token issued by the Auth API upon successful login or registration, used to authenticate subsequent requests.
- **Auth Token**: The JWT stored client-side (localStorage key `auth_token`) representing an active session.
- **Login Page**: The Portal page at `/login` where a returning user submits credentials.
- **Register Page**: The Portal page at `/register` where a new user creates an account.
- **User**: A person with a record in the `users` database table identified by a unique email address.
- **Credential Validation**: Server-side verification that the submitted email and bcrypt-hashed password match a `users` record.
- **Route Guard**: Client-side logic that checks for a valid Auth Token and redirects unauthenticated users to `/login`.

---

## Requirements

### Requirement 1 — Login Page UI

**User Story:** As a returning candidate, I want a login page with email and password fields, so that I can sign in to my account.

#### Acceptance Criteria

1. THE Portal SHALL render a login form at the `/login` route containing an email input, a password input, and a submit button.
2. WHEN the user submits the login form with an empty email or empty password field, THE Portal SHALL display an inline validation error message for each empty field without making a network request.
3. WHEN the user submits the login form with an invalid email format, THE Portal SHALL display an inline validation error message indicating the email format is invalid without making a network request.
4. WHILE the login form submission is in progress, THE Portal SHALL disable the submit button and display a loading indicator to prevent duplicate submissions.
5. THE Login Page SHALL include a visible link to the Register Page so that new users can navigate to account creation.

---

### Requirement 2 — User Registration

**User Story:** As a new candidate, I want to create an account with my full name, email, and password, so that I can access the portal.

#### Acceptance Criteria

1. THE Portal SHALL render a registration form at the `/register` route containing a full name input, an email input, a password input, a confirm-password input, and a submit button.
2. WHEN the user submits the registration form and the password field value does not match the confirm-password field value, THE Portal SHALL display an inline validation error and SHALL NOT submit the form to the Auth API.
3. WHEN the user submits the registration form with a password shorter than 8 characters, THE Portal SHALL display an inline validation error and SHALL NOT submit the form to the Auth API.
4. WHEN the user submits a valid registration form, THE Auth API SHALL create a new `users` record with the provided full name, email, and a bcrypt-hashed password, and SHALL return a JWT.
5. THE Register Page SHALL include a visible link to the Login Page so that existing users can navigate to sign in.

---

### Requirement 3 — Authentication API Endpoints

**User Story:** As the system, I want secure backend endpoints for login and registration, so that credentials are validated server-side and tokens are issued.

#### Acceptance Criteria

1. THE Auth API SHALL expose a `POST /api/v1/auth/login` endpoint that accepts an email and password, validates the credentials against the `users` table, and returns a signed JWT on success.
2. WHEN a login request is received with an email that does not exist in the `users` table or with a password that does not match the stored bcrypt hash, THE Auth API SHALL return an HTTP 401 response with a descriptive error detail.
3. THE Auth API SHALL expose a `POST /api/v1/auth/register` endpoint that accepts a full name, email, and password, creates a new `users` record with a bcrypt-hashed password, and returns a signed JWT.
4. WHEN a registration request is received with an email that already exists in the `users` table, THE Auth API SHALL return an HTTP 409 response with a descriptive error detail.
5. THE Auth API SHALL sign JWTs using a secret key from the application configuration and SHALL set a token expiry of 24 hours.

---

### Requirement 4 — Session Persistence and Route Protection

**User Story:** As an authenticated candidate, I want my session to persist across page refreshes and for protected pages to redirect me to login when I am not authenticated, so that my experience is seamless and secure.

#### Acceptance Criteria

1. WHEN a user successfully logs in or registers, THE Portal SHALL store the returned JWT in `localStorage` under the key `auth_token` and SHALL redirect the user to `/dashboard`.
2. WHEN an unauthenticated user navigates to any Portal route other than `/login` or `/register`, THE Portal SHALL redirect the user to `/login`.
3. WHEN an authenticated user navigates to `/login` or `/register`, THE Portal SHALL redirect the user to `/dashboard`.
4. WHEN the user clicks a logout action, THE Portal SHALL remove the `auth_token` from `localStorage` and SHALL redirect the user to `/login`.
5. THE Portal SHALL include the Auth Token as a `Bearer` token in the `Authorization` header of all Auth API requests made from authenticated pages.
