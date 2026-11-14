"""Entradas mal formadas nunca alcanzan los filtros de claves numéricas."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso
from apps.directorio_unidades.models.core import Unidad


class IdentificadoresDeGestionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('qa-ids', 'ids@example.org', 'clave')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de entradas', slug='qa-entradas',
            dependencia='laboratorios', descripcion='Prueba aislada', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='QA-ID-CUR', nombre='Curso de prueba',
            clasificacion='corto', publicado=True, inscripcion='abierta')
        cls.edicion = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo QA', anio=2026,
            inicio=date(2026, 12, 1), cupo=10)
        cls.inscripcion = InscripcionCurso.objects.create(edicion=cls.edicion, usuario=cls.admin, estado='aceptada')

    def setUp(self):
        self.client.force_login(self.admin)

    def test_gestion_de_matriculas_rechaza_ids_invalidos_sin_cambiar_la_inscripcion(self):
        url = reverse('inscritos_curso', args=[self.unidad.slug, self.curso.codigo])
        operaciones = [('aceptar', 'inscripcion'), ('asistencia', 'leccion'),
                       ('verificar_pago', 'pago'), ('cancelar_invitacion', 'invitacion'), ('matricular', 'edicion')]
        for accion, campo in operaciones:
            for valor in ('texto', '²', str(2**63), '9'*5000):
                with self.subTest(accion=accion, campo=campo, valor=valor[:25]):
                    datos = {'accion': accion, 'inscripcion': self.inscripcion.pk, 'asistio': '1', campo: valor}
                    self.assertEqual(self.client.post(url, datos).status_code, 404)
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.estado, 'aceptada')
        self.assertFalse(self.inscripcion.progresos.exists())

    def test_calidad_rechaza_las_claves_invalidas_antes_de_buscar_un_control(self):
        url = reverse('control_calidad', args=[self.unidad.slug])
        for campo in ('plan', 'lote_producto', 'lote_consumible', 'orden', 'hecho'):
            for valor in ('texto', '²', str(2**63), '9'*5000):
                with self.subTest(campo=campo, valor=valor[:25]):
                    self.assertEqual(self.client.get(url, {campo: valor}).status_code, 404)

    def test_planificacion_rechaza_reserva_y_actividad_invalidas(self):
        url = reverse('nueva_planificacion_practica', args=[self.unidad.slug])
        for campo in ('reserva', 'actividad'):
            for valor in ('texto', '²', str(2**63), '9'*5000):
                with self.subTest(campo=campo, valor=valor[:25]):
                    self.assertEqual(self.client.get(url, {campo: valor}).status_code, 404)

    def test_expediente_rechaza_documento_invalido(self):
        url = reverse('gestion_expediente_unidad', args=[self.unidad.slug])
        for valor in ('texto', '²', str(2**63), '9'*5000):
            with self.subTest(valor=valor[:25]):
                self.assertEqual(self.client.post(url, {'accion': 'anexos', 'documento': valor}).status_code, 404)

    def test_certificado_propio_rechaza_inscripcion_extrema(self):
        url = reverse('mi_certificado', args=[self.unidad.slug, self.curso.codigo])
        for valor in ('texto', '²', str(2**63), '9'*5000):
            with self.subTest(valor=valor[:25]):
                self.assertEqual(self.client.get(url, {'inscripcion': valor}).status_code, 404)
        self.assertFalse(self.inscripcion.certificados.exists())

    def test_calificar_rechaza_entrega_extrema(self):
        url = reverse('calificaciones_curso', args=[self.unidad.slug, self.curso.codigo])
        for valor in ('texto', '²', str(2**63), '9'*5000):
            with self.subTest(valor=valor[:25]):
                self.assertEqual(self.client.post(url, {'accion': 'calificar', 'entrega': valor,
                    'edicion': self.edicion.pk, 'nota_sobre_10': '8'}).status_code, 404)
