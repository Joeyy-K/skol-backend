# Skol - School ERP System (Backend)

![Django REST Framework](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=green)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

A robust and scalable backend for a complete school management system, built with Django and Django REST Framework.

**[View Live Frontend Demo](https://skol-frontend.vercel.app/)**

---

### About The Project

Skol was born from the need for a clean, modern, and user-friendly alternative to existing school management systems. This ERP is designed from the ground up to be intuitive for administrators, teachers, parents, and students, providing a seamless, integrated experience for managing all aspects of school life.

This repository contains the backend API, which serves as the brain of the entire system, handling business logic, data persistence, and security.


### Core Features

*   **Role-Based Access Control (RBAC):** Secure, distinct permissions and dashboards for Admins, Teachers, Students, and Parents.
*   **Complete Financial Module:**
    *   Fee Structure management per class and term.
    *   Automated Invoice generation.
    *   Payment tracking and status updates.
    *   Expense tracking by category.
    *   "Budget vs. Actual" reporting for financial planning.
*   **Academic Management:**
    *   Full CRUD for Classes, Subjects, Exams, and Academic Terms.
    *   Admin Gradebook Center for viewing class performance and publishing reports.
*   **Intelligent School Calendar:**
    *   A central, self-populating calendar that automatically creates events from other modules (Exams, Invoices, Schedules) via Django Signals.
    *   Smart summarization of repetitive events to maintain a clean UI.
    *   Role-based filtering to show relevant events to each user.
*   **Automated System Tasks:**
    *   Management commands for database population (`populate_db`, etc.).
    *   A daily cron job to automatically switch the active academic term.
    *   A notification engine to send reminders for upcoming events.
*   **Attendance & Scheduling:**
    *   Full system for managing school timetables (`TimeSlot`, `ScheduleEntry`).
    *   Daily attendance tracking, integrated with the holiday calendar to prevent errors.

### Getting Started

To get a local copy up and running, follow these simple steps.

**Prerequisites:**
*   Python 3.10+
*   PostgreSQL (or another database)

**Installation:**

1.  **Clone the repo:**
    ```sh
    git clone https://github.com/Joeyy-K/skol-backend.git
    cd skol-backend
    ```

2.  **Set up a virtual environment:**
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    *   Create a `.env` file in the project root by copying the example:
        ```sh
        cp .env.example .env
        ```
    *   Fill in the required variables in the `.env` file (Database URL, `SECRET_KEY`, etc.).

5.  **Run database migrations:**
    ```sh
    python manage.py migrate
    ```

6.  **(Optional) Populate the database with test data:**
    *   Run the master population script to create a full set of demo data.
    ```sh
    python manage.py populate_db --force
    ```

7.  **Run the development server:**
    ```sh
    python manage.py runserver
    ```
    The API will be available at `http://localhost:8000`.
