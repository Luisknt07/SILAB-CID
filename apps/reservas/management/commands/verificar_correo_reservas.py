from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.utils import timezone


class Command(BaseCommand):
    help = 'Verifica la configuración de correo de reservas y, opcionalmente, envía una prueba.'

    def add_arguments(self, parser):
        parser.add_argument('--enviar', action='store_true', help='Envía un mensaje de prueba.')
        parser.add_argument('--destinatario', help='Dirección que recibirá la prueba.')

    def handle(self, *args, **options):
        backend = settings.EMAIL_BACKEND
        datos = {
            'Backend': backend,
            'Servidor': f'{settings.EMAIL_HOST}:{settings.EMAIL_PORT}',
            'TLS': 'sí' if settings.EMAIL_USE_TLS else 'no',
            'Remitente': settings.DEFAULT_FROM_EMAIL,
            'URL del sistema': settings.SITE_URL,
            'Máximo de intentos': settings.RESERVATION_EMAIL_MAX_ATTEMPTS,
            'Intervalo de reintento': f'{settings.RESERVATION_EMAIL_RETRY_MINUTES} minutos',
        }
        for etiqueta, valor in datos.items():
            self.stdout.write(f'{etiqueta}: {valor}')

        if 'console.EmailBackend' in backend:
            self.stdout.write(self.style.WARNING(
                'El backend actual solo imprime mensajes en la consola; no los entrega a una bandeja real.'
            ))
        if 'smtp.EmailBackend' in backend and not settings.EMAIL_HOST_USER:
            self.stdout.write(self.style.WARNING('EMAIL_HOST_USER no está configurado.'))
        if 'smtp.EmailBackend' in backend and not settings.EMAIL_HOST_PASSWORD:
            self.stdout.write(self.style.WARNING('EMAIL_HOST_PASSWORD no está configurado.'))

        if not options['enviar']:
            self.stdout.write(self.style.SUCCESS('Configuración inspeccionada sin enviar correo.'))
            return

        destinatario = (options.get('destinatario') or '').strip()
        if not destinatario:
            raise CommandError('Usa --destinatario correo@dominio junto con --enviar.')
        try:
            validate_email(destinatario)
        except ValidationError as error:
            raise CommandError('El destinatario no es una dirección válida.') from error
        if 'console.EmailBackend' in backend:
            raise CommandError(
                'No se realizó la prueba: el backend de consola no entrega correos reales.'
            )
        if 'smtp.EmailBackend' in backend and (
            not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD
        ):
            raise CommandError(
                'No se realizó la prueba: faltan las credenciales EMAIL_HOST_USER o '
                'EMAIL_HOST_PASSWORD.'
            )

        enviado = EmailMultiAlternatives(
            '[UPEC Laboratorios] Prueba de correo transaccional',
            'La configuración de correo de reservas respondió correctamente.',
            settings.DEFAULT_FROM_EMAIL,
            [destinatario],
        ).send(fail_silently=False)
        if enviado != 1:
            raise CommandError('El backend no confirmó la entrega del mensaje de prueba.')
        self.stdout.write(self.style.SUCCESS(
            f'Prueba procesada para {destinatario} a las {timezone.localtime():%d/%m/%Y %H:%M:%S}.'
        ))
