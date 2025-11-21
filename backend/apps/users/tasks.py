# tasks.py
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

@shared_task
def send_email_template(subject, template_name, context, to_email):
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)  
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email="MediPoint@decodaai.com",
        to=[to_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()