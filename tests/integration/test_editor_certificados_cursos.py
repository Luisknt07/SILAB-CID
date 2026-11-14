"""El editor valida antes de guardar y cada certificado conserva su diseño e identidad."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from importlib.util import find_spec
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.formacion.presentation.certificados_cursos import emitir_si_corresponde, pdf_del_certificado
from apps.formacion.presentation.certificados_diseno import crear_diseno
from apps.formacion.presentation.certificados_forms import ConfiguracionCertificadoForm
from apps.formacion.models.cursos_certificacion import IMAGENES_CERTIFICADO
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.directorio_unidades.models.core import Unidad


class EditorCertificadoCursoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.gestor = User.objects.create_superuser('gestor-diseno', 'gestor@example.org', 'clave')
        cls.alumna = User.objects.create_user('alumna-diseno', 'alumna@example.org', 'clave', first_name='Ana')
        cls.otra = User.objects.create_user('otra-diseno', 'otra@example.org', 'clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio docente', slug='lab-diseno-cert',
                                           dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='CUR-DIS-001', nombre='Aplicaciones logísticas',
                                         duracion_horas=40, publicado=True)
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo A', anio=timezone.localdate().year,
                                                 inicio=timezone.localdate(), fin=timezone.localdate())
        cls.inscripcion = InscripcionCurso.objects.create(edicion=cls.edicion, usuario=cls.alumna, estado='aceptada',
                                                          nombres_completos='Ana Identidad de Matrícula', documento='DOC-PRIVADO-123')
        modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Inicio')
        cls.leccion = LeccionCurso.objects.create(modulo=modulo, titulo='Lectura', tipo='texto')

    def setUp(self):
        self.media = self.enterContext(TemporaryDirectory())
        self.enterContext(override_settings(MEDIA_ROOT=self.media))

    def url(self, nombre, *args):
        return reverse(nombre, args=[self.unidad.slug, self.curso.codigo, *args])

    def datos(self):
        configuracion = ConfiguracionCertificadoCurso(curso=self.curso)
        datos = {campo: getattr(configuracion, campo) for campo in ConfiguracionCertificadoForm.Meta.fields
                 if campo not in IMAGENES_CERTIFICADO and getattr(configuracion, campo) is not None}
        datos['mostrar_nota'] = 'on'
        datos['firma_nombre'] = 'Gabriela Ejemplo'
        datos['firma_cargo'] = 'Coordinación académica'
        return datos

    def png(self):
        salida = BytesIO()
        Image.new('RGBA', (400, 120), (20, 70, 50, 150)).save(salida, format='PNG')
        return salida.getvalue()

    def certificado(self, nota='81.23'):
        certificado = CertificadoCurso(inscripcion=self.inscripcion, codigo='CERT-MUES-TRA2',
                                       nombre=self.inscripcion.nombres_completos, documento=self.inscripcion.documento,
                                       curso_nombre=self.curso.nombre, clasificacion='Curso corto', horas=40,
                                       edicion=self.edicion.nombre, unidad_nombre=self.unidad.nombre,
                                       nota_final=Decimal(nota), firma_nombre='Firmante original', firma_cargo='Cargo original')
        configuracion = ConfiguracionCertificadoCurso.objects.filter(curso=self.curso).first()
        certificado.diseno_certificado = crear_diseno(certificado, configuracion)
        certificado.save()
        return certificado

    def test_editor_y_previa_exigen_gestor_y_previa_no_guarda_ni_emite(self):
        self.client.force_login(self.alumna)
        self.assertEqual(self.client.get(self.url('editar_certificado_curso')).status_code, 403)
        self.assertEqual(self.client.post(self.url('previsualizar_certificado_curso'), self.datos()).status_code, 403)
        self.client.force_login(self.gestor)
        editor = self.client.get(self.url('editar_certificado_curso') + '?embed=1')
        self.assertContains(editor, 'data-certificado-editor')
        self.assertContains(editor, 'data-previa-pdf')
        self.assertContains(editor, 'Los cambios actualizan la vista previa.')
        self.assertNotContains(editor, 'data-generar-previa')
        self.assertEqual(self.client.get(self.url('previsualizar_certificado_curso')).status_code, 405)
        respuesta = self.client.post(self.url('previsualizar_certificado_curso'), self.datos())
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
        self.assertIn('X-Certificado-Vista-Previa', respuesta)
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        self.assertFalse(CertificadoCurso.objects.exists())
        self.assertEqual(list(Path(self.media).rglob('*')), [])

    def test_guardar_exige_token_del_diseno_y_usuario_actual(self):
        self.client.force_login(self.gestor)
        datos = self.datos()
        self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 400)
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        token = previa['X-Certificado-Vista-Previa']
        datos['vista_previa_token'] = token
        datos['titulo_aprobacion'] = 'Un título sin revisar'
        self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 400)
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        datos['titulo_aprobacion'] = 'CERTIFICADO DE APROBACIÓN'
        datos['vista_previa_token'] = token + 'alterado'
        self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 400)
        datos['vista_previa_token'] = token
        respuesta = self.client.post(self.url('editar_certificado_curso') + '?embed=1', datos)
        self.assertEqual(respuesta.status_code, 302)
        configuracion = ConfiguracionCertificadoCurso.objects.get()
        self.assertEqual(configuracion.actualizado_por, self.gestor)
        self.assertEqual(configuracion.firma_nombre, 'Gabriela Ejemplo')
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_firma_pendiente_no_hereda_y_emite_sin_atribuir_una_persona(self):
        self.curso.firma_nombre = 'Firmante heredado'
        self.curso.firma_cargo = 'Cargo heredado'
        self.curso.save(update_fields=['firma_nombre', 'firma_cargo'])
        self.client.force_login(self.gestor)
        datos = self.datos()
        datos.pop('usar_firmante_curso')
        datos['firma_nombre'] = datos['firma_cargo'] = ''
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(previa.status_code, 200)
        datos['vista_previa_token'] = previa['X-Certificado-Vista-Previa']
        self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 302)
        configuracion = ConfiguracionCertificadoCurso.objects.get(curso=self.curso)
        self.assertFalse(configuracion.usar_firmante_curso)
        ProgresoLeccion.objects.create(inscripcion=self.inscripcion, leccion=self.leccion)
        with patch('apps.core.presentation.identidad.logo_institucional', return_value=None) as logo:
            certificado = emitir_si_corresponde(self.inscripcion)
        logo.assert_any_call(fondo='claro')
        logo.assert_any_call(fondo='oscuro')
        self.assertEqual(certificado.diseno_certificado['logo_institucional']['imagen'], '')
        self.assertEqual(certificado.diseno_certificado['firmantes'], [])
        self.assertEqual(certificado.firma_nombre, '')
        self.assertEqual(certificado.firma_cargo, '')
        self.assertTrue(pdf_del_certificado(certificado).startswith(b'%PDF'))
        configuracion.firma_nombre = 'Persona confirmada'
        configuracion.firma_cargo = 'Responsable académico'
        configuracion.save()
        certificado.refresh_from_db()
        self.assertEqual(certificado.diseno_certificado['firmantes'], [])

    def test_firma_explicita_requiere_nombre_y_admite_solo_segundo_firmante(self):
        datos = self.datos()
        datos.pop('usar_firmante_curso')
        datos['firma_nombre'] = ''
        formulario = ConfiguracionCertificadoForm(datos)
        self.assertFalse(formulario.is_valid())
        self.assertIn('firma_nombre', formulario.errors)
        datos['firma_cargo'] = ''
        datos['segunda_firma_nombre'] = 'Persona confirmada'
        datos['segunda_firma_cargo'] = 'Responsable académico'
        formulario = ConfiguracionCertificadoForm(datos)
        self.assertTrue(formulario.is_valid(), formulario.errors)
        certificado = self.certificado()
        diseno = crear_diseno(certificado, formulario.save(commit=False))
        self.assertEqual([firma['nombre'] for firma in diseno['firmantes']], ['Persona confirmada'])

    def test_variables_html_colores_e_imagenes_invalidas_se_rechazan(self):
        for texto in ('{nombre.__class__}', '{desconocida}', '{nombre!r}', '{nombre:>100}', '{curso', '<script>x</script>'):
            datos = self.datos()
            datos['texto_aprobacion'] = texto
            self.assertFalse(ConfiguracionCertificadoForm(datos).is_valid(), texto)
        for color in ('red', '#xyzxyz', '#ffffff'):
            datos = self.datos()
            datos['color_primario'] = color
            self.assertFalse(ConfiguracionCertificadoForm(datos).is_valid(), color)
        datos = self.datos()
        archivo = SimpleUploadedFile('firma.png', b'<svg>no es PNG</svg>', content_type='image/png')
        self.assertFalse(ConfiguracionCertificadoForm(datos, {'firma_imagen': archivo}).is_valid())

    def test_hash_incluye_la_imagen_y_la_firma_se_normaliza(self):
        self.client.force_login(self.gestor)
        datos = self.datos()
        datos['firma_imagen'] = SimpleUploadedFile('firma.png', self.png(), content_type='image/png')
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(previa.status_code, 200)
        token = previa['X-Certificado-Vista-Previa']
        datos = self.datos()
        datos['vista_previa_token'] = token
        # Quitar la imagen que sí se revisó cambia la huella.
        self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 400)
        datos['firma_imagen'] = SimpleUploadedFile('otra-ruta.jpg', self.png(), content_type='image/jpeg')
        self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 302)
        configuracion = ConfiguracionCertificadoCurso.objects.get()
        self.assertTrue(configuracion.firma_imagen.name.endswith('.png'))
        self.assertTrue(configuracion.firma_imagen.name.startswith('cursos/materiales/firmas_certificados/'))

    def test_emision_prioriza_identidad_de_matricula_y_congela_configuracion(self):
        configuracion = ConfiguracionCertificadoCurso.objects.create(curso=self.curso,
            titulo_participacion='CONSTANCIA DE FORMACIÓN', texto_participacion='Completó {curso} en {unidad}.',
            firma_nombre='Firmante del diseño', firma_cargo='Responsable docente')
        ProgresoLeccion.objects.create(inscripcion=self.inscripcion, leccion=self.leccion)
        certificado = emitir_si_corresponde(self.inscripcion)
        self.assertEqual(certificado.nombre, 'Ana Identidad de Matrícula')
        self.assertEqual(certificado.documento, 'DOC-PRIVADO-123')
        diseno = deepcopy(certificado.diseno_certificado)
        self.assertEqual(diseno['titulo'], 'CONSTANCIA DE FORMACIÓN')
        self.assertEqual(diseno['firmantes'][0]['nombre'], 'Firmante del diseño')
        ConfiguracionCertificadoCurso.objects.filter(pk=configuracion.pk).update(titulo_participacion='OTRO TÍTULO')
        Curso.objects.filter(pk=self.curso.pk).update(nombre='Otro curso')
        certificado.refresh_from_db()
        self.assertEqual(certificado.diseno_certificado, diseno)
        with patch('apps.core.presentation.identidad.identidad_actual', side_effect=AssertionError('No debe leer identidad actual')):
            self.assertTrue(pdf_del_certificado(certificado).startswith(b'%PDF'))

    def test_privacidad_gestor_y_propietario_por_grupo_aun_retirado(self):
        certificado = self.certificado()
        grupo_b = EdicionCurso.objects.create(curso=self.curso, nombre='Grupo B', anio=timezone.localdate().year)
        InscripcionCurso.objects.create(edicion=grupo_b, usuario=self.alumna, estado='aceptada')
        InscripcionCurso.objects.filter(pk=self.inscripcion.pk).update(estado='retirada')
        self.client.force_login(self.alumna)
        self.assertEqual(self.client.get(self.url('mi_certificado'), {'edicion': self.edicion.pk}).status_code, 200)
        self.assertEqual(self.client.get(self.url('mi_certificado'), {'edicion': grupo_b.pk}).status_code, 404)
        self.assertEqual(self.client.get(self.url('mi_certificado'), {'edicion': 'incorrecto'}).status_code, 404)
        self.assertEqual(self.client.get(self.url('certificado_curso_gestor', certificado.pk)).status_code, 403)
        self.client.force_login(self.otra)
        self.assertEqual(self.client.get(self.url('mi_certificado'), {'edicion': self.edicion.pk}).status_code, 404)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(self.url('certificado_curso_gestor', certificado.pk)).status_code, 200)
        self.client.logout()
        verificar = reverse('verificar_certificado', args=[certificado.codigo])
        pagina = self.client.get(verificar)
        self.assertNotContains(pagina, 'DOC-PRIVADO-123')
        self.assertNotContains(pagina, '8,123')
        self.assertNotContains(pagina, '81,23')
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado', return_value=b'%PDF-muestra') as generar:
            self.client.get(verificar, {'formato': 'pdf'})
            generar.assert_called_once_with(certificado, False)

    @skipUnless(find_spec('fitz'), 'La extracción visual de QA requiere PyMuPDF disponible en desarrollo.')
    def test_pdf_con_nombres_y_cargos_largos_no_recorta_y_oculta_documento_publico(self):
        import fitz
        configuracion = ConfiguracionCertificadoCurso.objects.create(curso=self.curso,
            firma_nombre=('Nombre compuesto de firmante de muestra ' * 5)[:160],
            firma_cargo=('Cargo académico institucional de muestra ' * 6)[:200],
            segunda_firma_nombre=('Segundo nombre compuesto de firmante ' * 5)[:160],
            segunda_firma_cargo=('Responsable académico de formación y transferencia ' * 5)[:200])
        configuracion.firma_imagen.save('original.png', ContentFile(self.png()), save=True)
        certificado = self.certificado('69.99')
        # Una emisión previa conserva su diseño, incluida la nota que entonces se mostraba.
        from apps.formacion.presentation.certificados_diseno import _crear_diseno_v1
        configuracion.mostrar_nota = True
        configuracion.texto_aprobacion = ('Aprobó el {tipo} «{curso}», con una duración de {horas} horas, '
                                           'dictado por {unidad}, en su edición {edicion}.')
        try:
            certificado.diseno_certificado = _crear_diseno_v1(certificado, configuracion)
        finally:
            configuracion.firma_imagen.close()
        certificado.nombre = ('Participante de nombre y apellidos compuestos ' * 5)[:200]
        privado = fitz.open(stream=pdf_del_certificado(certificado), filetype='pdf')
        publico = fitz.open(stream=pdf_del_certificado(certificado, False), filetype='pdf')
        self.assertEqual(len(privado), 1)
        self.assertIn('DOC-PRIVADO-123', privado[0].get_text())
        self.assertNotIn('DOC-PRIVADO-123', publico[0].get_text())
        self.assertIn('6,999/10', publico[0].get_text())
        self.assertIn('Segundo nombre compuesto', publico[0].get_text())
        diseno = deepcopy(certificado.diseno_certificado)
        configuracion.firma_imagen.delete(save=True)
        self.assertEqual(certificado.diseno_certificado, diseno)
        self.assertTrue(pdf_del_certificado(certificado).startswith(b'%PDF'))

    def test_previa_automatica_renderiza_solo_modalidad_visible_y_errores_son_privados(self):
        self.client.force_login(self.gestor)
        datos = dict(self.datos(), tipo_muestra='ponente')
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado', return_value=b'%PDF-muestra') as pdf:
            previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(previa.status_code, 200)
        self.assertEqual(pdf.call_count, 1)
        self.assertEqual(pdf.call_args.args[0].tipo, 'ponente')
        self.assertEqual(pdf.call_args.kwargs, {'mostrar_documento': False, 'vista_previa': True})
        self.assertIn('no-store', previa['Cache-Control'])
        datos['tema_fondo'] = 'no-existe'
        invalida = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(invalida.status_code, 400)
        self.assertIn('tema_fondo', invalida.json()['errores'])
        self.assertIn('private', invalida['Cache-Control'])
        self.assertIn('no-store', invalida['Cache-Control'])
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_guardado_ajax_conserva_la_modalidad_revisada_y_no_acepta_token_de_otra(self):
        self.client.force_login(self.gestor)
        datos = dict(self.datos(), tipo_muestra='asistencia')
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(previa.status_code, 200)
        datos['vista_previa_token'] = previa['X-Certificado-Vista-Previa']
        datos['tipo_muestra'] = 'organizador'
        rechazo = self.client.post(self.url('editar_certificado_curso'), datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(rechazo.status_code, 400)
        self.assertFalse(rechazo.json()['ok'])
        self.assertIn('__all__', rechazo.json()['errores'])
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        datos['tipo_muestra'] = 'asistencia'
        guardado = self.client.post(self.url('editar_certificado_curso') + '?embed=1', datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(guardado.status_code, 200)
        self.assertTrue(guardado.json()['ok'])
        self.assertTrue(guardado.json()['url'].endswith('?embed=1&guardado=1'))
        self.assertIn('no-store', guardado['Cache-Control'])
        self.assertEqual(ConfiguracionCertificadoCurso.objects.get().actualizado_por, self.gestor)

    def test_token_caducado_y_de_otro_actor_o_curso_no_guardan(self):
        self.client.force_login(self.gestor)
        datos = self.datos()
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        datos['vista_previa_token'] = previa['X-Certificado-Vista-Previa']
        with patch('django.core.signing.time.time', return_value=timezone.now().timestamp() + 1802):
            self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 400)
        otro = get_user_model().objects.create_superuser('gestor-otro-token', 'otro-token@example.invalid', 'clave')
        self.client.force_login(otro)
        self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 400)
        self.client.force_login(self.gestor)
        curso_b = Curso.objects.create(unidad=self.unidad, codigo='CUR-DIS-OTRO', nombre=self.curso.nombre, duracion_horas=40)
        otra_url = reverse('editar_certificado_curso', args=[self.unidad.slug, curso_b.codigo])
        self.assertEqual(self.client.post(otra_url, datos).status_code, 400)
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())

    def test_cambios_del_contexto_heredado_exigen_nueva_vista_previa(self):
        self.client.force_login(self.gestor)
        datos = self.datos()
        datos['firma_nombre'] = datos['firma_cargo'] = ''
        cambios = [('nombre', 'Curso renombrado'), ('duracion_horas', 41), ('firma_nombre', 'Nueva responsable')]
        for campo, valor in cambios:
            with self.subTest(campo=campo):
                previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
                self.assertEqual(previa.status_code, 200)
                datos['vista_previa_token'] = previa['X-Certificado-Vista-Previa']
                anterior = getattr(self.curso, campo)
                Curso.objects.filter(pk=self.curso.pk).update(**{campo: valor})
                try:
                    self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 400)
                finally:
                    Curso.objects.filter(pk=self.curso.pk).update(**{campo: anterior})
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        datos['vista_previa_token'] = previa['X-Certificado-Vista-Previa']
        self.unidad.imagen.save('nueva-foto.png', ContentFile(self.png()), save=True)
        self.assertEqual(self.client.post(self.url('editar_certificado_curso'), datos).status_code, 400)
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())

    def test_scope_y_permiso_se_revalidan_despues_de_bloquear_el_curso(self):
        self.client.force_login(self.gestor)
        otro_lab = Unidad.objects.create(nombre='Otra unidad', slug='otra-unidad-lock', dependencia='laboratorios',
                                          descripcion='.', fecha_inicio=date(2026, 1, 1))
        Curso.objects.filter(pk=self.curso.pk).update(unidad=otro_lab)
        with patch('apps.formacion.presentation.certificados_cursos._curso_del_editor', return_value=self.curso):
            self.assertEqual(self.client.post(self.url('editar_certificado_curso'), self.datos()).status_code, 404)
        Curso.objects.filter(pk=self.curso.pk).update(unidad=self.unidad)
        with patch('apps.formacion.presentation.certificados_cursos._curso_del_editor', return_value=self.curso), \
                patch('apps.formacion.presentation.cursos.puede_crear_cursos', return_value=False):
            self.assertEqual(self.client.post(self.url('editar_certificado_curso'), self.datos()).status_code, 403)
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())

    def test_fondo_png_jpeg_tamano_y_formato_se_validan_antes_de_persistir(self):
        self.client.force_login(self.gestor)
        gif = BytesIO()
        Image.new('RGB', (20, 20), 'red').save(gif, format='GIF')
        invalidos = [b'<svg>no es PNG</svg>', gif.getvalue(), self.png() + b'0' * (2 * 1024 * 1024)]
        for contenido in invalidos:
            datos = self.datos()
            datos['imagen_fondo'] = SimpleUploadedFile('fondo.png', contenido, content_type='image/png')
            respuesta = self.client.post(self.url('previsualizar_certificado_curso'), datos)
            self.assertEqual(respuesta.status_code, 400)
            self.assertIn('imagen_fondo', respuesta.json()['errores'])
        jpeg = BytesIO()
        Image.new('RGB', (1900, 1400), 'navy').save(jpeg, format='JPEG')
        datos = self.datos()
        datos['imagen_fondo'] = SimpleUploadedFile('fondo.jpg', jpeg.getvalue(), content_type='image/jpeg')
        form = ConfiguracionCertificadoForm(datos, {'imagen_fondo': datos.pop('imagen_fondo')}, instance=ConfiguracionCertificadoCurso(curso=self.curso))
        self.assertTrue(form.is_valid(), form.errors)
        fondo = form.cleaned_data['imagen_fondo']
        with Image.open(fondo) as normalizada:
            self.assertEqual(normalizada.format, 'PNG')
            self.assertLessEqual(normalizada.width, 1600)
            self.assertLessEqual(normalizada.height, 1200)
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        self.assertFalse(CertificadoCurso.objects.exists())
        self.assertEqual(list(Path(self.media).rglob('*')), [])

    def test_cambiar_fondo_no_pierde_logos_firmas_ni_certificados_emitidos(self):
        self.client.force_login(self.gestor)
        config = ConfiguracionCertificadoCurso.objects.create(curso=self.curso,
            firma_nombre='Primera firmante', firma_cargo='Coordinación',
            segunda_firma_nombre='Segunda firmante', segunda_firma_cargo='Dirección',
            tercera_firma_nombre='Tercera firmante', tercera_firma_cargo='Docencia')
        for campo in IMAGENES_CERTIFICADO:
            getattr(config, campo).save('original.png', ContentFile(self.png()), save=False)
        config.save()
        originales = {campo: getattr(config, campo).name for campo in IMAGENES_CERTIFICADO}
        certificado = self.certificado()
        snapshot = deepcopy(certificado.diseno_certificado)
        datos = {campo: getattr(config, campo) for campo in ConfiguracionCertificadoForm.Meta.fields
                 if campo not in IMAGENES_CERTIFICADO and getattr(config, campo) is not None}
        datos['diseno'] = 'ondas_tecnologicas'
        datos['imagen_fondo'] = SimpleUploadedFile('fondo-nuevo.png', self.png(), content_type='image/png')
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(previa.status_code, 200)
        datos['vista_previa_token'] = previa['X-Certificado-Vista-Previa']
        # Enviar otro nombre de archivo no cambia el contenido normalizado que se revisó.
        datos['imagen_fondo'] = SimpleUploadedFile('otro-nombre.png', self.png(), content_type='image/png')
        with self.captureOnCommitCallbacks(execute=True):
            guardado = self.client.post(self.url('editar_certificado_curso'), datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(guardado.status_code, 200, guardado.content)
        config.refresh_from_db()
        for campo, nombre in originales.items():
            if campo == 'imagen_fondo':
                self.assertNotEqual(getattr(config, campo).name, nombre)
                self.assertFalse(getattr(config, campo).storage.exists(nombre))
            else:
                self.assertEqual(getattr(config, campo).name, nombre)
                self.assertTrue(getattr(config, campo).storage.exists(nombre))
        certificado.refresh_from_db()
        self.assertEqual(certificado.diseno_certificado, snapshot)
        self.assertEqual(snapshot['version'], 12)
        self.assertTrue(snapshot['imagen_fondo'])
        self.assertTrue(pdf_del_certificado(certificado).startswith(b'%PDF'))

    def test_guardar_valida_otros_roles_y_error_ajax_no_guarda_archivos(self):
        self.client.force_login(self.gestor)
        datos = dict(self.datos(), tipo_muestra='asistencia')
        def renderizar(muestra, **kwargs):
            if muestra.tipo == 'organizador':
                raise ValidationError('El texto del rol no cabe de forma legible.')
            return b'%PDF-muestra'
        with patch('apps.formacion.presentation.certificados_cursos.pdf_del_certificado', side_effect=renderizar):
            datos['imagen_fondo'] = SimpleUploadedFile('fondo.png', self.png(), content_type='image/png')
            previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
            self.assertEqual(previa.status_code, 200)
            datos['vista_previa_token'] = previa['X-Certificado-Vista-Previa']
            datos['imagen_fondo'] = SimpleUploadedFile('fondo.png', self.png(), content_type='image/png')
            rechazo = self.client.post(self.url('editar_certificado_curso'), datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(rechazo.status_code, 400)
        self.assertFalse(rechazo.json()['ok'])
        self.assertIn('organización', rechazo.json()['errores']['__all__'][0]['message'].casefold())
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        self.assertFalse(CertificadoCurso.objects.exists())
        self.assertEqual(list(Path(self.media).rglob('*')), [])

    def test_cambio_concurrente_de_logo_no_se_sobrescribe_ni_se_borra_con_token_antiguo(self):
        self.client.force_login(self.gestor)
        config = ConfiguracionCertificadoCurso.objects.create(curso=self.curso)
        config.logo_2_imagen.save('antes.png', ContentFile(self.png()), save=True)
        datos = self.datos()
        previa = self.client.post(self.url('previsualizar_certificado_curso'), datos)
        self.assertEqual(previa.status_code, 200)
        datos['vista_previa_token'] = previa['X-Certificado-Vista-Previa']
        salida = BytesIO()
        Image.new('RGBA', (400, 120), (120, 30, 50, 255)).save(salida, format='PNG')
        config.logo_2_imagen.save('cambio-otro-gestor.png', ContentFile(salida.getvalue()), save=True)
        vigente = config.logo_2_imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            rechazo = self.client.post(self.url('editar_certificado_curso'), datos, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(rechazo.status_code, 400)
        config.refresh_from_db()
        self.assertEqual(config.logo_2_imagen.name, vigente)
        self.assertTrue(config.logo_2_imagen.storage.exists(vigente))
        self.assertEqual(config.actualizado_por, None)
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_subir_y_quitar_la_misma_imagen_rechaza_intencion_contradictoria(self):
        for campo in IMAGENES_CERTIFICADO:
            with self.subTest(campo=campo):
                datos = self.datos()
                datos['quitar_' + campo] = 'on'
                if campo.startswith('logo_'):
                    datos[campo.replace('_imagen', '_nombre')] = 'Institución colaboradora'
                archivo = SimpleUploadedFile('imagen.png', self.png(), content_type='image/png')
                formulario = ConfiguracionCertificadoForm(datos, {campo: archivo},
                    instance=ConfiguracionCertificadoCurso(curso=self.curso))
                self.assertFalse(formulario.is_valid())
                self.assertIn('quitar', ' '.join(formulario.errors[campo]))
        self.assertFalse(ConfiguracionCertificadoCurso.objects.exists())
        self.assertEqual(list(Path(self.media).rglob('*')), [])
