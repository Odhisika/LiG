Django E-commerce app

```markdown
# Django eCommerce App

Welcome to the **Django eCommerce App**, a scalable and customizable online store built with Django. This project provides a strong foundation for developers to create robust e-commerce platforms. 

---

## Getting Started

To get started with this project, follow the instructions below:

### Prerequisites
Ensure you have Python installed on your system. Additionally, it's a good practice to work within a virtual environment.

### Setting Up the Virtual Environment
1. Navigate to your project directory.
2. Run the following commands:
    ```bash
    python -m venv venv
    source venv/bin/activate  # For macOS/Linux
    venv\Scripts\activate     # For Windows
    ```

3. After activating the virtual environment, you're ready to install the project's dependencies.

---

## Installation

### Install Dependencies
Install the necessary dependencies listed in the `requirements.txt` file by running:

```bash
pip install -r requirements.txt
```

### Project Dependencies
Here’s a list of the dependencies included in this project:

- `asgiref`
- `certifi`
- `chardet`
- `Django`
- `django-admin-honeypot`
- `django-admin-thumbnails`
- `django-session-timeout`
- `idna`
- `Pillow`
- `python-decouple`
- `pytz==2020.1`
- `requests`
- `six`
- `sqlparse`
- `urllib3`

---

## Description of the Project

The **Django eCommerce App** is a web application designed to facilitate the buying and selling of products online. It features user authentication, an admin panel for managing products and orders, and a polished user interface for seamless shopping experiences. 

Whether you're developing a niche marketplace or a full-fledged online store, this app provides a great starting point.

---



-`Create a .env file and update this with your own details`
-`EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'`
-`EMAIL_HOST='smtp.gmail.com'`
-`EMAIL_PORT=587`
-`EMAIL_HOST_USER='yourmail@gmail.com'`
-`EMAIL_HOST_PASSWORD='your password'`
-`EMAIL_USE_TLS=True`
