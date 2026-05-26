# Implementation Plan

- [x] 1. Add JWT config and auth Pydantic schemas





  - Add `JWT_SECRET_KEY`, `JWT_ALGORITHM`, and `JWT_EXPIRE_HOURS` fields to `config.py` Settings class
  - Create `schemas/auth.py` with `RegisterRequest`, `LoginRequest`, and `TokenResponse` Pydantic v2 models; add `password` min-length validator (8 chars) on `RegisterRequest`
  - _Requirements: 3.3, 3.5_

- [x] 2. Implement the auth API router





- [x] 2.1 Create `api/routers/auth.py` with register and login endpoints


  - `POST /register`: hash password with bcrypt, INSERT into `users`, return JWT on success, raise HTTP 409 on duplicate email
  - `POST /login`: SELECT user by email, verify bcrypt hash, return JWT on success, raise HTTP 401 on mismatch
  - Use `python-jose` for JWT signing with `sub=user_id`, `exp=now+JWT_EXPIRE_HOURS`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 2.2 Mount the auth router in `main.py`


  - Import and include `auth.router` under the `/api/v1` prefix
  - _Requirements: 3.1, 3.3_

- [x] 2.3 Write unit tests for auth endpoints


  - Test register success, duplicate email 409, login success, wrong password 401
  - _Requirements: 3.1, 3.2, 3.3, 3.4_
-

- [x] 3. Update `get_current_user_id` dependency to decode JWT







  - Modify `api/dependencies.py`: read `Authorization: Bearer <token>` header, decode JWT using `python-jose`, extract `sub` as UUID, raise HTTP 401 for missing/invalid/expired tokens
  - Remove the `_DEFAULT_USER_ID` stub from `api/routers/practice.py` and replace the `get_current_user_id` local definition with an import from `api/dependencies.py`
  - _Requirements: 3.5, 4.2, 4.5_

- [x] 3.1 Write unit tests for the updated dependency





  - Test valid token returns correct UUID, missing token raises 401, expired token raises 401
  - _Requirements: 3.5, 4.2_

- [x] 4. Add auth helper functions and types to the frontend








- [x] 4.1 Add `TokenResponse` type to `frontend/types/auth.ts`


  - Create the file with the `TokenResponse` interface
  - _Requirements: 4.1_

- [x] 4.2 Add `loginUser`, `registerUser`, and `authHeaders` to `frontend/lib/api.ts`


  - `authHeaders()`: reads `localStorage["auth_token"]` and returns `{ Authorization: "Bearer <token>" }`
  - `loginUser(email, password)`: POST to `/api/v1/auth/login`, returns `TokenResponse`
  - `registerUser(fullName, email, password)`: POST to `/api/v1/auth/register`, returns `TokenResponse`
  - Update all existing fetch calls in `api.ts` to spread `authHeaders()` into their headers
  - _Requirements: 4.1, 4.5_

- [x] 5. Build the Login page





  - Create `frontend/app/login/page.tsx` as a `"use client"` component
  - Render email + password inputs with inline validation (empty field, invalid email format)
  - On submit: call `loginUser`, store JWT in `localStorage["auth_token"]`, redirect to `/dashboard`
  - Show loading state on submit button; display API error messages inline
  - Include a link to `/register`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1_

- [x] 5.1 Write component tests for LoginPage


  - Test field validation errors, loading state, success redirect, and API error display
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 6. Build the Register page





  - Create `frontend/app/register/page.tsx` as a `"use client"` component
  - Render full name, email, password, and confirm-password inputs with inline validation (empty fields, email format, password min 8 chars, passwords match)
  - On submit: call `registerUser`, store JWT in `localStorage["auth_token"]`, redirect to `/dashboard`
  - Show loading state on submit button; display API error messages inline
  - Include a link to `/login`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.1_

- [x] 6.1 Write component tests for RegisterPage


  - Test all validation rules, loading state, success redirect, and duplicate email error
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 7. Implement AuthGuard and route protection





  - Create `frontend/components/AuthGuard.tsx` as a `"use client"` component: reads `localStorage["auth_token"]` on mount; redirects to `/login` if absent; renders children if present
  - Update `frontend/app/layout.tsx` to wrap `<main>` with `<AuthGuard>` but exclude `/login` and `/register` paths from the guard (check `usePathname`)
  - Update `frontend/app/page.tsx` root redirect to point to `/login` instead of `/dashboard` (the guard will redirect authenticated users to `/dashboard`)
  - _Requirements: 4.2, 4.3_

- [x] 8. Add logout to the Sidebar





  - Update `frontend/components/Sidebar.tsx` to add a logout button at the bottom
  - On click: remove `auth_token` from `localStorage`, redirect to `/login` using `useRouter`
  - _Requirements: 4.4_
