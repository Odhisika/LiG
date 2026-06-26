from django.conf import settings


def build_csp_policy(request):
    policies = getattr(settings, 'CSP_POLICIES', {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            'https://challenges.cloudflare.com',
            'https://cdn.tailwindcss.com',
            'https://cdnjs.cloudflare.com',
            'https://code.jquery.com',
            'https://cdn.jsdelivr.net',
            'https://stackpath.bootstrapcdn.com',
            'https://kit.fontawesome.com',
            'https://cdn.ckeditor.com',
            'https://www.paypal.com',
            'https://www.paypalobjects.com',
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            'https://cdnjs.cloudflare.com',
            'https://cdn.tailwindcss.com',
            'https://stackpath.bootstrapcdn.com',
            'https://cdn.jsdelivr.net',
            'https://fonts.googleapis.com',
            'https://kit.fontawesome.com',
        ],
        'img-src': [
            "'self'",
            'data:',
            'blob:',
            'https://images.unsplash.com',
        ],
        'font-src': [
            "'self'",
            'https://fonts.gstatic.com',
            'https://cdnjs.cloudflare.com',
            'https://cdn.jsdelivr.net',
            'https://stackpath.bootstrapcdn.com',
            'data:',
        ],
        'frame-src': [
            "'self'",
            'https://challenges.cloudflare.com',
            'https://www.paypal.com',
            'https://www.google.com',
        ],
        'connect-src': [
            "'self'",
            'https://www.paypal.com',
        ],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
    })

    if settings.DEBUG:
        policies.get('connect-src', []).append('ws://localhost:*')
        policies.get('connect-src', []).append('http://localhost:*')

    return '; '.join(
        f"{key} {' '.join(values)}"
        for key, values in policies.items()
    )
