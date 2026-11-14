"""Configuración de videollamadas sin importar controladores del aula.

La cabecera global solo necesita el origen público, almacenado cinco minutos.
Las claves permanecen en la configuración interna y no se incluyen en caché.
"""
from django.conf import settings
from django.core.cache import cache

from apps.formacion.models.cursos import ServidorClasesEnVivo

CLAVE_ORIGEN = 'clases-en-vivo-origen'


def configuracion():
    """El servicio vigente y sus credenciales: lo guardado en la plataforma y, si no hay, las variables de entorno."""
    fila = ServidorClasesEnVivo.objects.order_by('pk').first()
    if fila is not None and fila.listo:
        return {'proveedor': fila.proveedor, 'samba_equipo': fila.samba_equipo, 'samba_clave': fila.samba_clave,
                'samba_dominio': fila.samba_dominio, 'daily_api_key': fila.daily_api_key,
                'daily_dominio': fila.daily_dominio, 'bbb_url': fila.bbb_url, 'bbb_secreto': fila.bbb_secreto,
                'bbb_checksum': fila.bbb_checksum}
    if settings.CLASES_EN_VIVO_DAILY_API_KEY:
        return {'proveedor': 'daily', 'daily_api_key': settings.CLASES_EN_VIVO_DAILY_API_KEY,
                'daily_dominio': settings.CLASES_EN_VIVO_DAILY_DOMINIO}
    if settings.CLASES_EN_VIVO_BBB_URL and settings.CLASES_EN_VIVO_BBB_SECRETO:
        return {'proveedor': 'bbb', 'bbb_url': settings.CLASES_EN_VIVO_BBB_URL,
                'bbb_secreto': settings.CLASES_EN_VIVO_BBB_SECRETO,
                'bbb_checksum': settings.CLASES_EN_VIVO_BBB_CHECKSUM or 'sha1'}
    return {'proveedor': ''}


def configurado():
    return bool(configuracion()['proveedor'])


def _origen(url):
    if not url or '://' not in url:
        return ''
    esquema, resto = url.split('://', 1)
    return f'{esquema}://{resto.split("/", 1)[0]}'


def origen_del_servidor():
    """El origen al que el aula deja usar cámara, micrófono y pantalla compartida; se guarda unos minutos en caché
    porque lo consulta cada respuesta."""
    def calcular():
        conf = configuracion()
        if conf['proveedor'] == 'samba':
            return f"https://{conf['samba_dominio']}" if conf.get('samba_dominio') else ''
        if conf['proveedor'] == 'daily':
            return f"https://{conf['daily_dominio']}" if conf.get('daily_dominio') else ''
        return _origen(conf.get('bbb_url', ''))
    return cache.get_or_set(CLAVE_ORIGEN, calcular, 300)


def olvidar_origen():
    cache.delete(CLAVE_ORIGEN)
