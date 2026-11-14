"""Certificados profesionales: identidad congelada y acreditaciones con permisos y respaldo."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.formacion.presentation.certificados_cursos import _huella_previa, _muestra_certificado, direccion_de_verificacion, emitir_certificado_evento, emitir_si_corresponde
from apps.formacion.presentation.certificados_forms import AcreditacionCertificadoForm, ConfiguracionCertificadoForm
from apps.formacion.models.cursos_certificacion import IMAGENES_CERTIFICADO
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso, LeccionCurso, ModuloCurso, ProgresoLeccion
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.directorio_unidades.models.core import Unidad


class CertificadosProfesionalesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.gestor = User.objects.create_superuser('gestor-eventos-cert', 'gestor@example.invalid', 'clave')
        cls.alumna = User.objects.create_user('alumna-eventos-cert', 'alumna@example.invalid', 'clave')
        cls.otra = User.objects.create_user('otra-eventos-cert', 'otra@example.invalid', 'clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de eventos', slug='lab-eventos-cert',
                                           dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='EVENT-CERT-001', nombre='Jornada de logística',
                                         duracion_horas=8, publicado=True)
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='Jornada 2026', anio=2026,
                                                  inicio=date(2026, 10, 1), fin=date(2026, 10, 2),
                                                  horas_certificadas=Decimal('7.50'))
        cls.inscripcion = InscripcionCurso.objects.create(edicion=cls.edicion, usuario=cls.alumna, estado='aceptada',
                                                          nombres_completos='Ana Participante', documento='PRIVADO-123')
        cls.otra_inscripcion = InscripcionCurso.objects.create(edicion=cls.edicion, usuario=cls.otra, estado='aceptada')
        cls.modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Preparación')
        cls.lectura = LeccionCurso.objects.create(modulo=cls.modulo, titulo='Lectura pendiente', tipo='texto')

    def setUp(self):
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))

    def datos_diseno(self, **cambios):
        configuracion = ConfiguracionCertificadoCurso(curso=self.curso)
        datos = {campo: getattr(configuracion, campo) for campo in ConfiguracionCertificadoForm.Meta.fields
                 if campo not in IMAGENES_CERTIFICADO and getattr(configuracion, campo) is not None}
        datos.update(cambios)
        return datos

    def png(self):
        salida = BytesIO()
        Image.new('RGBA', (600, 180), '#245d3a').save(salida, format='PNG')
        return salida.getvalue()

    def emitir(self, **cambios):
        datos = {'tipo': 'ponente', 'motivo': 'Ponencia registrada en el programa de la jornada.', 'confirmacion': True}
        datos.update(cambios)
        return emitir_certificado_evento(self.inscripcion, self.gestor, **datos)

    def test_ponente_exige_gestor_motivo_confirmacion_y_no_aprobacion_ficticia(self):
        with self.assertRaises(PermissionDenied):
            emitir_certificado_evento(self.inscripcion, self.alumna, 'ponente', 'Registro comprobado de la ponencia.', True)
        for cambios in ({'tipo': 'aprobacion'}, {'motivo': ''}, {'confirmacion': False}, {'motivo': '<script>registro</script>'}):
            with self.subTest(cambios=cambios), self.assertRaises(ValidationError):
                self.emitir(**cambios)
        self.assertFalse(CertificadoCurso.objects.exists())
        certificado = self.emitir()
        self.assertEqual(certificado.tipo, 'ponente')
        self.assertIsNone(certificado.nota_final)
        self.assertTrue(certificado.emision_manual)
        self.assertEqual(certificado.emitido_por, self.gestor)
        self.assertFalse(ProgresoLeccion.objects.exists())
        self.assertIn('programa', certificado.motivo_emision)

    def test_emision_congela_fechas_horas_decimales_y_rol_sin_nota(self):
        configuracion = ConfiguracionCertificadoCurso.objects.create(curso=self.curso, categoria_evento='jornada',
            fecha_inicio=date(2026, 9, 1), fecha_fin=date(2026, 9, 2), horas_certificadas=Decimal('6.25'), mostrar_nota=True)
        certificado = self.emitir()
        self.assertEqual((certificado.fecha_inicio, certificado.fecha_fin, certificado.horas),
                         (self.edicion.inicio, self.edicion.fin, Decimal('7.50')))
        self.assertEqual(certificado.categoria_evento, 'jornada')
        self.assertFalse(certificado.diseno_certificado['mostrar_nota'])
        self.assertIn('ponente', certificado.diseno_certificado['texto'])
        congelado = deepcopy(certificado.diseno_certificado)
        EdicionCurso.objects.filter(pk=self.edicion.pk).update(horas_certificadas=99, inicio=date(2026, 10, 8))
        ConfiguracionCertificadoCurso.objects.filter(pk=configuracion.pk).update(diseno='congreso', categoria_evento='congreso')
        certificado.refresh_from_db()
        self.assertEqual(certificado.diseno_certificado, congelado)
        self.assertEqual(certificado.horas, Decimal('7.50'))

    def test_auto_sin_fechas_u_horas_no_emite_y_manual_explica_completar(self):
        ProgresoLeccion.objects.create(inscripcion=self.inscripcion, leccion=self.lectura)
        EdicionCurso.objects.filter(pk=self.edicion.pk).update(inicio=None, fin=None, horas_certificadas=None)
        Curso.objects.filter(pk=self.curso.pk).update(duracion_horas=None)
        self.assertIsNone(emitir_si_corresponde(self.inscripcion))
        with self.assertRaisesMessage(ValidationError, 'fecha inicial'):
            self.emitir()
        ConfiguracionCertificadoCurso.objects.create(curso=self.curso, fecha_inicio=date(2026, 10, 1),
                                                      fecha_fin=date(2026, 10, 2), horas_certificadas=Decimal('3.25'))
        certificado = emitir_si_corresponde(self.inscripcion)
        self.assertEqual(certificado.horas, Decimal('3.25'))
        self.assertEqual(certificado.tipo, 'participacion')

    def test_auto_aprobacion_no_sustituye_evaluacion_y_no_concede_ponente(self):
        ProgresoLeccion.objects.create(inscripcion=self.inscripcion, leccion=self.lectura)
        ConfiguracionCertificadoCurso.objects.create(curso=self.curso, tipo_certificado='aprobacion')
        self.assertIsNone(emitir_si_corresponde(self.inscripcion))
        ConfiguracionCertificadoCurso.objects.filter(curso=self.curso).update(tipo_certificado='ponente')
        self.assertIsNone(emitir_si_corresponde(self.inscripcion))
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_inscripcion_no_aceptada_no_se_acredita(self):
        InscripcionCurso.objects.filter(pk=self.inscripcion.pk).update(estado='pendiente')
        with self.assertRaisesMessage(ValidationError, 'aceptada'):
            self.emitir()
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_colision_codigo_reintenta_y_unico_por_grupo_evitan_duplicados(self):
        CertificadoCurso.objects.create(inscripcion=self.otra_inscripcion, codigo='CERT-AAAA-AAAA',
            nombre='Otra persona', curso_nombre=self.curso.nombre, clasificacion='Jornada',
            edicion=self.edicion.nombre, unidad_nombre=self.unidad.nombre)
        with patch('apps.formacion.presentation.certificados_cursos.nuevo_codigo', side_effect=['CERT-AAAA-AAAA', 'CERT-BBBB-BBBB']):
            certificado = self.emitir()
        self.assertEqual(certificado.codigo, 'CERT-BBBB-BBBB')
        self.assertEqual(self.emitir().pk, certificado.pk)
        with self.assertRaisesMessage(ValidationError, 'otra modalidad'):
            self.emitir(tipo='organizador')
        self.assertEqual(CertificadoCurso.objects.filter(inscripcion=self.inscripcion, anulado=False).count(), 1)

    def test_anular_y_reemitir_preserva_el_rol_manual_y_codigo_nuevo(self):
        certificado = self.emitir()
        self.client.force_login(self.gestor)
        args = [self.unidad.slug, self.curso.codigo, certificado.pk]
        self.client.post(reverse('anular_certificado', args=args), {'motivo': 'Corrección de nombre'})
        self.client.post(reverse('reemitir_certificado', args=args))
        certificado.refresh_from_db()
        nuevo = CertificadoCurso.objects.get(inscripcion=self.inscripcion, anulado=False)
        self.assertTrue(certificado.anulado)
        self.assertNotEqual(nuevo.codigo, certificado.codigo)
        self.assertEqual(nuevo.tipo, 'ponente')
        self.assertTrue(nuevo.emision_manual)
        self.assertIsNone(nuevo.nota_final)
        self.assertEqual(nuevo.emitido_por, self.gestor)

    def test_endpoint_manual_restringe_actor_curso_y_metodo(self):
        url = reverse('emitir_certificado_manual', args=[self.unidad.slug, self.curso.codigo])
        datos = {'inscripcion': self.inscripcion.pk, 'tipo': 'asistencia',
                 'motivo': 'Asistencia respaldada en el registro del evento.', 'confirmacion': '1'}
        self.client.force_login(self.alumna)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.client.force_login(self.gestor)
        self.assertEqual(self.client.get(url).status_code, 405)
        otro = Curso.objects.create(unidad=self.unidad, codigo='EVENT-CERT-OTRO', nombre='Otro evento')
        otro_url = reverse('emitir_certificado_manual', args=[self.unidad.slug, otro.codigo])
        self.assertEqual(self.client.post(otro_url, datos).status_code, 404)
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.assertEqual(CertificadoCurso.objects.get().tipo, 'asistencia')

    def test_logo_tercera_firma_y_datos_nuevos_forman_parte_de_huella(self):
        datos = self.datos_diseno(fecha_inicio='2026-10-01', fecha_fin='2026-10-02', horas_certificadas='2.50',
                                  tercera_firma_nombre='Tercera firmante', tercera_firma_cargo='Responsable académica',
                                  logo_4_posicion='derecha', logo_4_nombre='Institución aliada registrada', disposicion_logos='entre_extremos')
        archivos = {'logo_4_imagen': SimpleUploadedFile('logo.png', self.png(), content_type='image/png'),
                    'tercera_firma_imagen': SimpleUploadedFile('firma.png', self.png(), content_type='image/png')}
        form = ConfiguracionCertificadoForm(datos, archivos, instance=ConfiguracionCertificadoCurso(curso=self.curso))
        self.assertTrue(form.is_valid(), form.errors)
        config = form.save(commit=False)
        huella = _huella_previa(config, self.curso, self.gestor)
        config.logo_4_posicion = 'izquierda'
        self.assertNotEqual(_huella_previa(config, self.curso, self.gestor), huella)
        config.logo_4_posicion = 'derecha'
        config.horas_certificadas = Decimal('2.75')
        self.assertNotEqual(_huella_previa(config, self.curso, self.gestor), huella)
        config.save()
        self.assertIn('logos_certificados/', config.logo_4_imagen.name)
        self.assertIn('firmas_certificados/', config.tercera_firma_imagen.name)
        self.assertFalse(config.mostrar_nota)

    def test_formulario_rechaza_fechas_horas_html_nota_e_imagen_disfrazada(self):
        for cambios in ({'fecha_inicio': '2026-10-02', 'fecha_fin': '2026-10-01'},
                        {'horas_certificadas': '-1'}, {'horas_certificadas': '2001'},
                        {'texto_ponente': '{nota}'}, {'tercera_firma_nombre': '<b>persona</b>'},
                        {'tercera_firma_cargo': 'Sin nombre'}):
            with self.subTest(cambios=cambios):
                self.assertFalse(ConfiguracionCertificadoForm(self.datos_diseno(**cambios)).is_valid())
        falso = SimpleUploadedFile('logo.png', b'<svg>no es PNG</svg>', content_type='image/png')
        self.assertFalse(ConfiguracionCertificadoForm(self.datos_diseno(), {'logo_1_imagen': falso}).is_valid())
        self.assertFalse(AcreditacionCertificadoForm({'inscripcion': 1, 'tipo': 'aprobacion', 'motivo': 'Registro real', 'confirmacion': True}).is_valid())

    @override_settings(SITE_URL='https://laboratorios.example.edu.ec')
    def test_qr_congela_url_configurada_y_verificacion_no_expone_identidad_privada(self):
        certificado = self.emitir()
        direccion = direccion_de_verificacion(certificado)
        self.assertEqual(direccion, 'https://laboratorios.example.edu.ec' + reverse('verificar_certificado', args=[certificado.codigo]))
        with override_settings(SITE_URL='https://otro.example.edu.ec'):
            self.assertEqual(direccion_de_verificacion(certificado), direccion)
        self.client.logout()
        pagina = self.client.get(reverse('verificar_certificado', args=[certificado.codigo]))
        self.assertContains(pagina, 'Ana Participante')
        self.assertNotContains(pagina, 'PRIVADO-123')
        self.assertEqual(self.client.get(reverse('verificar_certificado', args=['CERT-ZZZZ-ZZZZ'])).status_code, 404)

    def test_preview_incompleto_es_solo_muestra_sin_emision(self):
        muestra = _muestra_certificado(self.curso, ConfiguracionCertificadoCurso(curso=self.curso), 'organizador')
        self.assertIsNone(muestra.fecha_inicio)
        self.assertIsNone(muestra.fecha_fin)
        self.assertEqual(muestra.diseno_certificado['periodo'], 'Período por definir')
        self.assertIsNone(muestra.pk)
        self.assertFalse(CertificadoCurso.objects.exists())
        self.assertFalse(muestra.diseno_certificado['mostrar_nota'])

    def test_categoria_invalida_no_emite_ni_rompe_el_aula(self):
        ProgresoLeccion.objects.create(inscripcion=self.inscripcion, leccion=self.lectura)
        ConfiguracionCertificadoCurso.objects.create(curso=self.curso, categoria_evento='inventada')
        self.assertIsNone(emitir_si_corresponde(self.inscripcion))
        with self.assertRaisesMessage(ValidationError, 'tipo de actividad válido'):
            self.emitir()
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_reemision_manual_incompleta_muestra_error_sin_duplicar(self):
        certificado = self.emitir()
        CertificadoCurso.objects.filter(pk=certificado.pk).update(anulado=True)
        EdicionCurso.objects.filter(pk=self.edicion.pk).update(fin=None)
        self.client.force_login(self.gestor)
        respuesta = self.client.post(reverse('reemitir_certificado', args=[self.unidad.slug, self.curso.codigo, certificado.pk]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(CertificadoCurso.objects.count(), 1)
        self.assertFalse(CertificadoCurso.objects.filter(anulado=False).exists())
        from django.contrib.messages import get_messages
        self.assertTrue(any('fecha inicial' in str(mensaje) for mensaje in get_messages(respuesta.wsgi_request)))
