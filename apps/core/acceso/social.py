import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.conf import settings

# Nunca print(): una consola de Windows sin UTF-8 falla al escribir símbolos y
# ese error interrumpía el inicio de sesión.
registro = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def _provider_name(self, sociallogin):
        provider_map = {
            'google': 'Google',
            'microsoft': 'Microsoft',
        }
        return provider_map.get(sociallogin.account.provider, sociallogin.account.provider.capitalize())

    def _get_social_email(self, sociallogin):
        data = sociallogin.account.extra_data or {}
        return (
            data.get('email')
            or data.get('preferred_username')
            or data.get('userPrincipalName')
            or data.get('upn')
        )

    def _get_allowed_domains(self):
        domains = getattr(settings, 'ALLOWED_SOCIAL_EMAIL_DOMAINS', ['gmail.com', 'upec.edu.ec', 'labs.upec.edu.ec'])
        return [d.lower() for d in domains]

    def _email_domain(self, email):
        if not email or '@' not in email:
            return ''
        return email.split('@')[-1].strip().lower()

    def _classify_email_type(self, email):
        domain = self._email_domain(email)
        if domain == 'gmail.com':
            return 'gmail'
        if domain == 'upec.edu.ec' or domain.endswith('.upec.edu.ec'):
            return 'upec'
        return 'other'

    def _is_allowed_domain(self, email):
        domain = self._email_domain(email)
        if not email or '@' not in email:
            return False
        allowed_domains = self._get_allowed_domains()
        return domain in allowed_domains

    def _assign_user_segment(self, user, email):
        email_type = self._classify_email_type(email)
        upec_group_name = getattr(settings, 'SOCIAL_UPEC_GROUP_NAME', 'UsuariosUPEC')
        gmail_group_name = getattr(settings, 'SOCIAL_GMAIL_GROUP_NAME', 'UsuariosGmail')

        # Asegura que no queden grupos de segmentación conflictivos
        groups_to_remove = Group.objects.filter(name__in=[upec_group_name, gmail_group_name])
        if groups_to_remove.exists():
            user.groups.remove(*groups_to_remove)

        if email_type == 'upec':
            group, _ = Group.objects.get_or_create(name=upec_group_name)
            user.groups.add(group)
        elif email_type == 'gmail':
            group, _ = Group.objects.get_or_create(name=gmail_group_name)
            user.groups.add(group)

        try:
            from apps.core.models.usuarios_base import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if email_type == 'upec':
                profile.institucion = 'UPEC'
            elif email_type == 'gmail':
                profile.institucion = 'Gmail'
            profile.save(update_fields=['institucion'])
        except Exception as e:
            registro.warning('No se pudo segmentar el perfil del usuario %s: %s', user.pk, e)

    def _correo_acreditado(self, sociallogin):
        """Indica si el proveedor responde por el correo con el que se identifica la persona."""
        if sociallogin.account.provider == 'google':
            datos = sociallogin.account.extra_data or {}
            return bool(datos.get('email_verified') or datos.get('verified_email'))
        # Microsoft se identifica por el nombre principal de la cuenta, cuyo
        # dominio pertenece al directorio que la emite y figura entre los permitidos.
        return True

    def _asegurar_cuenta_existente(self, request, usuario, email):
        """Evita que quien registró antes un correo ajeno conserve acceso a la cuenta.

        Cualquiera puede crear una cuenta con contraseña usando el correo de
        otra persona. Si ese correo nunca se confirmó, la contraseña pudo
        ponerla un tercero: se anula al vincular al titular que acredita el
        proveedor. Las cuentas de personal las crea la administración.
        """
        from allauth.account.models import EmailAddress
        from django.db import IntegrityError, transaction

        confirmado = EmailAddress.objects.filter(user=usuario, email__iexact=email, verified=True).exists()
        if confirmado:
            return
        if usuario.has_usable_password() and not (usuario.is_staff or usuario.is_superuser):
            usuario.set_unusable_password()
            usuario.save(update_fields=['password'])
            messages.info(
                request,
                'Por seguridad se desactivó la contraseña anterior de esta cuenta, porque su correo no '
                'se había confirmado. Puedes definir una nueva con «¿Olvidaste tu contraseña?».'
            )
        try:
            with transaction.atomic():
                direccion = EmailAddress.objects.filter(user=usuario, email__iexact=email).first()
                if direccion is None:
                    EmailAddress.objects.create(
                        user=usuario, email=email, verified=True,
                        primary=not EmailAddress.objects.filter(user=usuario, primary=True).exists())
                else:
                    direccion.verified = True
                    direccion.save(update_fields=['verified'])
        except IntegrityError:
            # Otra cuenta ya confirmó este correo; no se altera su registro.
            pass

    def pre_social_login(self, request, sociallogin):
        """
        Invocado antes del login social para manejar usuarios duplicados
        """
        # Si el usuario ya está conectado, no hacer nada
        if sociallogin.is_existing:
            return
        
        # Obtener el email de la cuenta social
        email = self._get_social_email(sociallogin)
        provider_name = self._provider_name(sociallogin)

        if email and not self._is_allowed_domain(email):
            messages.error(
                request,
                f'Solo se permiten cuentas @gmail.com o @upec.edu.ec para iniciar sesión con {provider_name}.'
            )
            raise ImmediateHttpResponse(redirect('account_login'))

        if email and not self._correo_acreditado(sociallogin):
            messages.error(
                request,
                f'{provider_name} no confirma que ese correo te pertenezca. Verifícalo en tu cuenta de '
                f'{provider_name} e intenta de nuevo.'
            )
            raise ImmediateHttpResponse(redirect('account_login'))

        if email:
            # Buscar usuarios existentes con este email
            existing_users = User.objects.filter(email=email)
            
            if existing_users.count() > 1:
                # Si hay múltiples usuarios, usar el más reciente
                registro.warning('Varias cuentas comparten el correo del acceso social; se usa la más reciente.')
                existing_user = existing_users.order_by('-date_joined').first()
            elif existing_users.count() == 1:
                existing_user = existing_users.first()
            else:
                # No hay usuarios existentes, continuar con el flujo normal
                return
            
            # Conectar la cuenta social al usuario existente
            try:
                self._asegurar_cuenta_existente(request, existing_user, email)
                sociallogin.connect(request, existing_user)
                self._assign_user_segment(existing_user, email)
                registro.info('Acceso social vinculado a la cuenta existente %s.', existing_user.pk)
                messages.success(
                    request, 
                    f'Tu cuenta de {provider_name} ha sido conectada a tu usuario existente: {existing_user.email}'
                )
            except Exception:
                registro.exception('No se pudo vincular el acceso social a la cuenta %s.', existing_user.pk)
                messages.error(request, f'Error conectando tu cuenta de {provider_name}. Intenta de nuevo.')

    def save_user(self, request, sociallogin, form=None):
        """
        Guarda un usuario recién registrado con datos de Google
        """
        # Verificar una vez más que no existe un usuario con este email
        email = self._get_social_email(sociallogin)
        provider_name = self._provider_name(sociallogin)

        if email and not self._is_allowed_domain(email):
            messages.error(
                request,
                f'Solo se permiten cuentas @gmail.com o @upec.edu.ec para iniciar sesión con {provider_name}.'
            )
            raise ImmediateHttpResponse(redirect('account_login'))
        
        if email:
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                self._assign_user_segment(existing_user, email)
                registro.warning('La cuenta %s ya existía al guardar el acceso social.', existing_user.pk)
                return existing_user
        
        # Crear nuevo usuario
        user = super().save_user(request, sociallogin, form)
        
        # Auto-completar información del perfil desde Google/Microsoft
        social_data = sociallogin.account.extra_data
        
        # Actualizar nombre completo si no está definido
        if not user.first_name and social_data.get('given_name'):
            user.first_name = social_data.get('given_name')
        elif not user.first_name and social_data.get('name'):
            user.first_name = social_data.get('name').split(' ')[0]
        
        if not user.last_name and social_data.get('family_name'):
            user.last_name = social_data.get('family_name')
        
        # Generar username único si está vacío o duplicado
        if not user.username or User.objects.filter(username=user.username).exclude(pk=user.pk).exists():
            base_username = email.split('@')[0] if email else 'user'
            username = base_username
            counter = 1
            
            while User.objects.filter(username=username).exclude(pk=user.pk).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user.username = username
            registro.info('Nombre de usuario generado para el acceso social.')
        
        user.save()
        if email:
            self._assign_user_segment(user, email)
        
        # Crear perfil extendido si no existe
        try:
            from apps.core.models.usuarios_base import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            if created:
                registro.info('Perfil creado para la cuenta %s.', user.pk)
        except Exception as e:
            registro.warning('No se pudo crear el perfil de la cuenta %s: %s', user.pk, e)
        
        return user
    
    def get_login_redirect_url(self, request):
        """Tras entrar con el correo institucional se completan los datos.

        El proveedor solo entrega el nombre y el correo; el resto identifica a
        quien usará los laboratorios y sin él no se puede reservar.
        """
        from apps.core.usuarios.vigencia import perfil_vigente

        if not perfil_vigente(request.user):
            messages.info(
                request,
                'Completa tus datos institucionales para usar los laboratorios: '
                'tipo de usuario, facultad, carrera y, si eres estudiante, '
                'semestre y código.',
            )
            return '/profile/?completar=1'
        messages.success(request, '¡Bienvenido! Has iniciado sesión correctamente.')
        return '/'
    
    def is_auto_signup_allowed(self, request, sociallogin):
        """Permitir auto-registro siempre"""
        return True
    
    def populate_username(self, request, user):
        """Generar username automático y único"""
        email = user.email
        if email:
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            
            # Asegurar que sea único
            while User.objects.filter(username=username).exclude(pk=user.pk).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user.username = username
            registro.info('Nombre de usuario asignado para el acceso social.')
    
    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """Manejo de errores de autenticación"""
        registro.warning('Error de autenticación con el proveedor %s: %s', provider_id, error)
        provider_name = provider_id.capitalize() if provider_id else 'el proveedor'
        messages.error(request, f'Error al autenticar con {provider_name}. Por favor, intenta de nuevo.')
        return redirect('account_login')

    def new_user(self, request, sociallogin):
        """Personalizar la creación de nuevos usuarios"""
        user = super().new_user(request, sociallogin)
        
        # Asegurar que el email esté definido
        social_email = self._get_social_email(sociallogin)
        if not user.email and social_email:
            user.email = social_email
        
        return user
