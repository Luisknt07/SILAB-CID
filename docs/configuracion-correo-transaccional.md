# Configuración pendiente del correo transaccional

El sistema ya genera y conserva el comprobante HTML de cada solicitud. Para
entregar la misma información por correo falta obtener y configurar las
credenciales institucionales. Ningún secreto debe guardarse en Git.

## Datos que debe proporcionar o confirmar la Dirección de TIC

1. **Buzón de servicio**: una cuenta institucional dedicada, por ejemplo
   `sistema.labs@upec.edu.ec`. No se recomienda usar la contraseña personal de
   un administrador.
2. **Servidor y puerto SMTP**: para la configuración propuesta se espera
   `smtp.office365.com`, puerto `587` y cifrado STARTTLS. TIC debe confirmar que
   esos datos corresponden al tenant institucional.
3. **Usuario de autenticación**: normalmente es la dirección completa del
   buzón de servicio.
4. **Secreto de autenticación**: contraseña exclusiva de aplicación o secreto
   entregado para ese buzón. Debe almacenarse únicamente como variable de
   entorno del servidor.
5. **Permiso de envío**: el buzón debe tener autorizado SMTP autenticado y
   permiso para enviar con la dirección definida en `DEFAULT_FROM_EMAIL`.
6. **Política de autenticación**: confirmar si la institución permite SMTP con
   credencial de aplicación. Si exige OAuth o Microsoft Graph, no se debe usar
   una contraseña normal; habrá que habilitar ese proveedor antes del envío.
7. **Conectividad**: permitir desde el servidor la resolución DNS y la salida
   TCP por el puerto SMTP autorizado.
8. **URL pública**: dominio HTTPS definitivo de la plataforma. Los correos la
   utilizan para abrir el comprobante y el seguimiento.

## Variables que se configuran en el servidor

Crear el archivo `.env` de despliegue a partir de `.env-example` y completar:

```dotenv
SITE_URL=https://laboratorios.upec.edu.ec
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_HOST_USER=sistema.labs@upec.edu.ec
EMAIL_HOST_PASSWORD=SECRETO_ENTREGADO_POR_TIC
EMAIL_USE_TLS=True
EMAIL_TIMEOUT=20
DEFAULT_FROM_EMAIL=sistema.labs@upec.edu.ec
REQUIRE_TRANSACTIONAL_EMAIL=True
```

El valor de `EMAIL_HOST_PASSWORD` mostrado es solo una indicación; nunca debe
copiarse literalmente ni publicarse.

## Validación antes de activar

```powershell
.\.venv\Scripts\python.exe manage.py check --deploy --settings=config.settings_production
.\.venv\Scripts\python.exe manage.py verificar_correo_reservas
```

Cuando TIC confirme la cuenta y autorice una prueba real:

```powershell
.\.venv\Scripts\python.exe manage.py verificar_correo_reservas --enviar --destinatario correo.prueba@upec.edu.ec
```

La activación se considera completa solo si el comando confirma la entrega y
el mensaje llega a la bandeja de entrada. Después se puede habilitar el
programador de recordatorios sin la opción `-SinCorreo`.
