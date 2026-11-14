"""Contenido de certificados: fechas naturales y actualización selectiva de defaults."""
from datetime import date
from importlib import import_module
from types import SimpleNamespace

from tests.historia import registro_anterior

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.formacion.presentation.certificados_cursos import _huella_previa, _muestra_certificado, periodo_actividad, presentar_fecha
from apps.formacion.presentation.certificados_forms import ConfiguracionCertificadoForm
from apps.formacion.models.cursos import CertificadoCurso, Curso, EdicionCurso, InscripcionCurso
from apps.formacion.models.cursos_certificacion import ConfiguracionCertificadoCurso
from apps.directorio_unidades.models.core import Unidad
from apps.formacion.models.cursos_certificacion import IMAGENES_CERTIFICADO, TIPOS_CERTIFICADO


class FechasCertificadoTests(SimpleTestCase):
    def test_fecha_larga_en_espanol_no_depende_del_locale(self):
        self.assertEqual(presentar_fecha(date(2026, 10, 1)), '1 de octubre de 2026')
        self.assertEqual(presentar_fecha(date(2028, 2, 29)), '29 de febrero de 2028')
        self.assertEqual(presentar_fecha(None), '')

    def test_periodos_mismo_dia_mes_y_cruces_de_mes_y_anio(self):
        casos = [
            (date(2026, 10, 1), date(2026, 10, 1), 'el 1 de octubre de 2026'),
            (date(2026, 10, 1), date(2026, 10, 3), 'del 1 al 3 de octubre de 2026'),
            (date(2026, 9, 28), date(2026, 10, 2), 'del 28 de septiembre al 2 de octubre de 2026'),
            (date(2026, 12, 28), date(2027, 1, 2), 'del 28 de diciembre de 2026 al 2 de enero de 2027'),
        ]
        for inicio, fin, esperado in casos:
            with self.subTest(inicio=inicio, fin=fin):
                self.assertEqual(periodo_actividad(inicio, fin), esperado)
        self.assertEqual(periodo_actividad(None, date(2026, 10, 2)), '')
        self.assertEqual(periodo_actividad(date(2026, 10, 1), None), '')
        with self.assertRaises(ValidationError):
            periodo_actividad(date(2026, 10, 2), date(2026, 10, 1))


class ContenidoCertificadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('contenido-cert', 'contenido@example.invalid', 'clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio docente', slug='lab-contenido-cert',
            dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='CONT-CERT-001', nombre='Curso de logística', duracion_horas=8)
        cls.otro_curso = Curso.objects.create(unidad=cls.unidad, codigo='CONT-CERT-002', nombre='Curso personalizado')
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='Edición A', anio=2026)
        cls.inscripcion = InscripcionCurso.objects.create(edicion=cls.edicion, usuario=cls.usuario, estado='aceptada')

    def test_migracion_actualiza_solo_defaults_exactos_y_preserva_certificados(self):
        migracion = import_module('apps.historial_modelos.migrations.0319_certificados_profesionales')
        anteriores = {campo: textos[0][0] for campo, textos in migracion.TEXTOS_PREDETERMINADOS.items()}
        personalizados = {campo: 'Redacción propia de coordinación: ' + campo for campo in anteriores}
        normal = ConfiguracionCertificadoCurso.objects.create(curso=self.curso, **anteriores)
        personalizada = ConfiguracionCertificadoCurso.objects.create(curso=self.otro_curso, **personalizados)
        snapshot = {'version': 2, 'texto': 'Texto histórico con su composición original', 'fecha_inicio': '01/10/2026'}
        certificado = CertificadoCurso.objects.create(inscripcion=self.inscripcion, codigo='CERT-CONT-ANT2',
            nombre='Participante histórico', curso_nombre=self.curso.nombre, clasificacion='Curso',
            edicion='Edición A', unidad_nombre=self.unidad.nombre, diseno_certificado=snapshot)
        editor = SimpleNamespace(connection=connection)
        migracion.actualizar_textos_predeterminados(registro_anterior(), editor)
        normal.refresh_from_db()
        personalizada.refresh_from_db()
        certificado.refresh_from_db()
        for campo, (_, nuevo) in migracion.TEXTOS_PREDETERMINADOS.items():
            self.assertEqual(getattr(normal, campo), nuevo)
            self.assertEqual(getattr(personalizada, campo), personalizados[campo])
        self.assertEqual(certificado.diseno_certificado, snapshot)
        migracion.restaurar_textos_predeterminados(registro_anterior(), editor)
        normal.refresh_from_db()
        personalizada.refresh_from_db()
        for campo, (viejos, _) in migracion.TEXTOS_PREDETERMINADOS.items():
            self.assertEqual(getattr(normal, campo), viejos[-1])
            self.assertEqual(getattr(personalizada, campo), personalizados[campo])

    def test_formulario_acepta_variables_nuevas_y_huella_incluye_emisor_y_entradilla(self):
        configuracion = ConfiguracionCertificadoCurso(curso=self.curso)
        datos = {campo: getattr(configuracion, campo) for campo in ConfiguracionCertificadoForm.Meta.fields
            if campo not in IMAGENES_CERTIFICADO and getattr(configuracion, campo) is not None}
        datos.update(emisor='Facultad responsable', entradilla='{emisor} otorga el presente certificado a',
                     texto_aprobacion='{curso}, {periodo}, {horas} horas; emitido el {fecha_emision}.')
        form = ConfiguracionCertificadoForm(datos, instance=configuracion)
        self.assertTrue(form.is_valid(), form.errors)
        configuracion = form.save(commit=False)
        huella = _huella_previa(configuracion, self.curso, self.usuario)
        configuracion.emisor = 'Otra facultad'
        self.assertNotEqual(_huella_previa(configuracion, self.curso, self.usuario), huella)
        configuracion.emisor = 'Facultad responsable'
        configuracion.entradilla = 'Concede el presente certificado a'
        self.assertNotEqual(_huella_previa(configuracion, self.curso, self.usuario), huella)
        datos['emisor'] = '<b>Institución</b>'
        self.assertFalse(ConfiguracionCertificadoForm(datos, instance=ConfiguracionCertificadoCurso(curso=self.curso)).is_valid())

    def test_cinco_modalidades_incluyen_periodo_horas_y_emisor_en_el_parrafo(self):
        configuracion = ConfiguracionCertificadoCurso(curso=self.curso, emisor='Facultad responsable',
            fecha_inicio=date(2026, 10, 1), fecha_fin=date(2026, 10, 3), horas_certificadas='7.50')
        for tipo, _ in TIPOS_CERTIFICADO:
            with self.subTest(tipo=tipo):
                muestra = _muestra_certificado(self.curso, configuracion, tipo)
                diseno = muestra.diseno_certificado
                self.assertEqual(diseno['version'], 12)
                self.assertIn('del 1 al 3 de octubre de 2026', diseno['texto'])
                self.assertIn('7,5', diseno['texto'])
                self.assertIn('Facultad responsable', diseno['texto'])
                self.assertEqual(diseno['emisor'], 'Facultad responsable')
                self.assertEqual(diseno['entradilla'], 'Otorga el presente certificado a')
                self.assertNotIn('{periodo}', diseno['texto'])
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_muestra_con_solo_fecha_final_no_inventa_un_rango_invertido(self):
        configuracion = ConfiguracionCertificadoCurso(curso=self.curso, fecha_fin=date(2025, 4, 5))
        muestra = _muestra_certificado(self.curso, configuracion)
        self.assertIsNone(muestra.fecha_inicio)
        self.assertEqual(muestra.fecha_fin, date(2025, 4, 5))
        self.assertEqual(muestra.diseno_certificado['periodo'], 'Período por definir')
        self.assertIn('período por definir', muestra.diseno_certificado['texto'])
        self.assertEqual(muestra.diseno_certificado['fecha_fin'], '5 de abril de 2025')
        self.assertEqual(muestra.diseno_certificado['emisor'], self.unidad.nombre)
        self.assertFalse(CertificadoCurso.objects.exists())

    def test_verificacion_publica_emisor_congelado_y_fallback_legado_sin_datos_privados(self):
        certificado = CertificadoCurso.objects.create(inscripcion=self.inscripcion, codigo='CERT-CONT-EMI3',
            nombre='Participante de muestra', documento='DOC-PRIVADO-456', nota_final='82.30',
            curso_nombre=self.curso.nombre, clasificacion='Curso', edicion='Edición A', unidad_nombre=self.unidad.nombre,
            diseno_certificado={'version': 3, 'emisor': 'Facultad de organización de muestra'})
        url = reverse('verificar_certificado', args=[certificado.codigo])
        for version in (3, 2, 1):
            with self.subTest(version=version):
                if version < 3:
                    CertificadoCurso.objects.filter(pk=certificado.pk).update(diseno_certificado={'version': version})
                pagina = self.client.get(url)
                self.assertContains(pagina, 'Facultad de organización de muestra' if version == 3 else self.unidad.nombre)
                self.assertNotContains(pagina, 'DOC-PRIVADO-456')
                self.assertNotContains(pagina, 'Calificación')
                self.assertNotContains(pagina, '82,30')
