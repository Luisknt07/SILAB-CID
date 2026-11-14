"""La URL directa no elude propiedad, embargo ni visibilidad documental."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.centros_id.models import CentroID, DocumentoCentro, Resultado, CarpetaCentro, RecursoCentro
from apps.directorio_unidades.models.core import Unidad
from apps.finanzas.models.finanzas import MovimientoFinancieroUnidad
from apps.recursos.models.recursos import Archivo
from apps.core.models.usuarios_base import UserProfile
from apps.gestion_unidades.models.espacios import ResponsableUnidad


class MediaPrivadaTests(TestCase):
    def setUp(self):
        medios = TemporaryDirectory()
        self.addCleanup(medios.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=medios.name))
        self.owner = get_user_model().objects.create_user('dueño')
        self.other = get_user_model().objects.create_user('ajeno')
        self.unit = Unidad.objects.create(nombre='Unidad privada', slug='media-privada',
                                         dependencia='laboratorios', fecha_inicio=date.today(), administrador=self.owner)
        self.center = CentroID.objects.create(nombre='Centro privado', slug='centro-privado', area='digital', proposito='Pruebas')

    def archivo(self, nombre):
        ruta = Path(settings.MEDIA_ROOT, nombre)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(b'contenido')
        return nombre

    def get(self, nombre):
        response = self.client.get('/media/' + nombre)
        if response.streaming:
            b''.join(response.streaming_content)
        return response

    def test_archivos_sin_registro_incluidos_comprobantes_no_se_publican(self):
        for nombre in ('huerfano.pdf', 'finanzas/comprobantes/privado.pdf', 'cursos/comprobantes/privado.pdf'):
            self.assertEqual(self.get(self.archivo(nombre)).status_code, 404)

    def test_comprobante_financiero_exige_delegacion_de_la_unidad(self):
        nombre = self.archivo('finanzas/comprobantes/factura.pdf')
        MovimientoFinancieroUnidad.objects.create(unidad=self.unit, tipo='ingreso', categoria='servicio', monto=5,
                                                  fecha_movimiento=date.today(), descripcion='Prueba', comprobante=nombre,
                                                  creado_por=self.owner, actualizado_por=self.owner)
        self.assertEqual(self.get(nombre).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.get(nombre).status_code, 404)
        self.client.force_login(self.owner)
        respuesta = self.get(nombre)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Cache-Control'], 'private, no-store')

    def test_avatar_no_expone_fotos_de_otro_usuario(self):
        nombre = self.archivo('profiles/avatars/privada.png')
        UserProfile.objects.update_or_create(user=self.owner, defaults={'avatar': nombre})
        self.owner.refresh_from_db()
        self.client.force_login(self.other)
        self.assertEqual(self.get(nombre).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.get(nombre).status_code, 200)

    def test_foto_de_responsable_no_publico_exige_titular_o_edicion_de_su_unidad(self):
        titular = get_user_model().objects.create_user('titular-foto-privada')
        delegado = get_user_model().objects.create_user('delegado-foto-privada')
        operador = get_user_model().objects.create_user('operador-sin-configuracion')
        self.other.is_staff = True
        self.other.save(update_fields=['is_staff'])
        Unidad.objects.create(nombre='Otra unidad QA', slug='otra-unidad-foto',
                              dependencia='laboratorios', fecha_inicio=date.today(), administrador=self.other)
        nombre = self.archivo('unidades/responsables/foto-interna.png')
        responsable = ResponsableUnidad.objects.create(unidad=self.unit, usuario=titular,
            nombre='Persona interna QA', foto=nombre, publico=False)
        ResponsableUnidad.objects.create(unidad=self.unit, usuario=delegado, rol='tecnico',
            permisos_operativos={'configuracion': True})
        ResponsableUnidad.objects.create(unidad=self.unit, usuario=operador, rol='tecnico',
            permisos_operativos={'configuracion': False})
        for persona in (None, self.other, operador):
            self.client.logout()
            if persona is not None:
                self.client.force_login(persona)
            for metodo, cabeceras in (('get', {}), ('head', {}), ('get', {'HTTP_RANGE': 'bytes=0-1'})):
                with self.subTest(usuario=getattr(persona, 'username', 'anonimo'), metodo=metodo,
                                  rango=bool(cabeceras)):
                    respuesta = getattr(self.client, metodo)('/media/' + nombre, **cabeceras)
                    try:
                        self.assertEqual(respuesta.status_code, 404)
                    finally:
                        if respuesta.streaming:
                            b''.join(respuesta.streaming_content)
        for persona in (titular, self.owner, delegado):
            self.client.force_login(persona)
            for metodo, cabeceras in (('get', {}), ('head', {}), ('get', {'HTTP_RANGE': 'bytes=0-1'})):
                with self.subTest(usuario=persona.username, metodo=metodo, rango=bool(cabeceras)):
                    respuesta = getattr(self.client, metodo)('/media/' + nombre, **cabeceras)
                    if respuesta.streaming:
                        b''.join(respuesta.streaming_content)
                    self.assertEqual(respuesta.status_code, 200)
                    self.assertEqual(respuesta['Cache-Control'], 'private, no-store')
        titular.is_active = False
        titular.save(update_fields=['is_active'])
        self.client.force_login(titular)
        self.assertEqual(self.get(nombre).status_code, 404)
        responsable.activo = False
        responsable.save(update_fields=['activo'])
        for persona in (titular, self.owner, delegado):
            self.client.force_login(persona)
            self.assertEqual(self.get(nombre).status_code, 404)

    def test_foto_publica_de_responsable_no_se_publica_en_unidad_inactiva(self):
        nombre = self.archivo('unidades/responsables/foto-publica.png')
        ResponsableUnidad.objects.create(unidad=self.unit, nombre='Persona publicada QA', foto=nombre, publico=True)
        self.assertEqual(self.get(nombre).status_code, 200)
        Unidad.objects.filter(pk=self.unit.pk).update(activo=False)
        self.assertEqual(self.get(nombre).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.get(nombre).status_code, 200)

    def test_documento_interno_y_resultado_bajo_embargo_no_se_abren_por_url(self):
        nombre = self.archivo('centros_id/documentos/interno.pdf')
        documento = DocumentoCentro.objects.create(centro=self.center, tipo='acta_comite', titulo='Privado',
                                                   publico=False, archivo=nombre)
        self.assertEqual(self.get(nombre).status_code, 404)
        documento.publico = True
        documento.save()
        self.assertEqual(self.get(nombre).status_code, 200)
        resultado = self.archivo('centros_id/resultados/embargo.pdf')
        registro = Resultado.objects.create(centro=self.center, tipo='publicacion', titulo='Embargo', anio=2026,
                                            acceso='restringido')
        # Simula un archivo legado/importado que preceda a la validación de save.
        Resultado.objects.filter(pk=registro.pk).update(archivo=resultado)
        self.assertEqual(self.get(resultado).status_code, 404)

    def test_carpeta_interna_o_inactiva_no_publica_sus_adjuntos(self):
        nombre = self.archivo('centros_id/recursos/interno.pdf')
        carpeta = CarpetaCentro.objects.create(centro=self.center, pestana='centro', nombre='Interna', visibilidad='interna')
        RecursoCentro.objects.create(carpeta=carpeta, titulo='Privado', archivo=nombre)
        self.assertEqual(self.get(nombre).status_code, 404)
        carpeta.visibilidad = 'publica'
        carpeta.save()
        self.assertEqual(self.get(nombre).status_code, 200)
        carpeta.activa = False
        carpeta.save()
        self.assertEqual(self.get(nombre).status_code, 404)

    def test_html_legacy_registrado_se_descarga_aislado_y_no_se_ejecuta_en_el_portal(self):
        nombre = self.archivo('recursos/archivos/carga.html')
        Archivo.objects.create(tipo='html', archivo=nombre)
        respuesta = self.get(nombre)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta['Content-Disposition'].startswith('attachment'))
        self.assertIn('sandbox', respuesta['Content-Security-Policy'])
        self.assertEqual(respuesta['X-Frame-Options'], 'SAMEORIGIN')

    def test_recorrido_de_directorios_no_elude_la_raiz(self):
        self.assertEqual(self.client.get('/media/../manage.py').status_code, 404)
