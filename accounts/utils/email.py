from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def send_html_email(subject, template_name, context, to):
    """
    Send an HTML email with a plain-text fallback.
    """
    # render HTML template with context
    html_content = render_to_string(template_name, context)

    # fallback plain text
    text_content = "Please use an email client that supports HTML."

    msg = EmailMultiAlternatives(subject, text_content, to=to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
