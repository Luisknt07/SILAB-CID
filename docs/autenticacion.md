# Autenticación y cuentas

La plataforma usa `django-allauth` con dos entradas: Google (y Microsoft
cuando se configure) y correo con contraseña. Las dos crean la misma cuenta de
Django con un `UserProfile`; el tipo de usuario, la facultad, la carrera y el
período vigente se completan en el perfil antes de poder reservar.

## Entrada social

- Los dominios admitidos se declaran en `ALLOWED_SOCIAL_EMAIL_DOMAINS`
  (`gmail.com`, `upec.edu.ec` y `labs.upec.edu.ec` por omisión).
- `webcitt/adapters.py` clasifica el correo: los institucionales entran al
  grupo `UsuariosUPEC` y los de Gmail a `UsuariosGmail`, y fija la institución
  del perfil. Si ya existe una cuenta con ese correo, la enlaza en lugar de
  duplicarla.
- Las credenciales del proveedor se cargan como `SocialApp` desde el
  administrador de Django; el `Site` debe corresponder al dominio real.

## Correo y contraseña

- El registro está abierto en `/accounts/signup/`. El correo es el
  identificador (`ACCOUNT_LOGIN_METHODS = {'email'}`) y es único.
- Google y Microsoft se inician mediante formularios POST con token CSRF; no
  se permite que una peticion GET modifique la sesion.
- En desarrollo no se verifica el correo. En producción
  (`config/settings_production.py`) la verificación es obligatoria antes de
  usar la cuenta: sin eso alguien podría registrar una dirección institucional
  ajena antes que su dueño. Google y Microsoft ya entregan el correo
  verificado, así que la entrada social no se detiene.
- Producción además impide enumerar cuentas (`ACCOUNT_PREVENT_ENUMERATION`).

## Quién es quién después de entrar

Hay tres tipos de usuario y nada más; la regla vive en
`webcitt/domains/unidades/permisos.py`:

- **Superusuario**: `is_superuser`. Administra toda la plataforma.
- **Personal de una unidad**: el administrador principal que designa la
  Universidad (`Unidad.administrador`) y los responsables con cuenta que la
  unidad registra desde su panel (`ResponsableUnidad`). Gestionan su unidad y
  solo ella; no entran al administrador de Django.
- **Usuario**: cualquier cuenta con perfil institucional vigente. Reserva, ve
  y cancela lo propio.

La única excepción es Decanato, que entra al administrador de Django solo para
revisar y amortizar las órdenes de servicio del FabLab; su continuidad está
pendiente de decisión institucional (ver `docs/unidades-y-centros-id.md`).

## Compuerta de perfil

`PerfilInstitucionalVigenteMiddleware` devuelve al perfil a quien intente usar
`/reservas/` sin datos completos y confirmados para el período en curso. El
panel de la unidad y el módulo de guías quedan fuera de la compuerta a
propósito: atender el trabajo de otros no puede detenerse por un dato del
perfil personal. El superusuario nunca queda fuera.
