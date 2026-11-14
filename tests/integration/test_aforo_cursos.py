"""La oferta de centros agrupa aforos sin conservar conteos al escribir matrículas."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.directorio_unidades.selectors import oferta_publica_para_centros
from apps.formacion.presentation.aforo_cursos import cupos_por_edicion
from apps.formacion.presentation.matriculas_cursos import cupos_disponibles
from apps.formacion.models.cursos import Curso, EdicionCurso, InscripcionCurso
from apps.formacion.models.cursos_inscripcion import InvitacionCurso
from apps.directorio_unidades.models.core import Unidad


class AforoCursosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user('aforo-auditoria')
        cls.unidad = Unidad.objects.create(nombre='Laboratorio de aforo', slug='laboratorio-aforo',
            dependencia='laboratorios', administrador=cls.usuario, descripcion='.', fecha_inicio=date(2026, 1, 1))
        cls.curso = Curso.objects.create(unidad=cls.unidad, codigo='AFORO-QA', nombre='Curso de aforo', publicado=True)
        cls.ediciones = [EdicionCurso.objects.create(curso=cls.curso, nombre=f'Grupo {i}', anio=2026, cupo=8)
                         for i in range(12)]

    def test_listado_de_doce_grupos_usa_dos_consultas_de_aforo(self):
        grupo = self.ediciones[0]
        aceptada = InscripcionCurso.objects.create(edicion=grupo, usuario=self.usuario, estado='aceptada')
        InvitacionCurso.objects.create(edicion=grupo, correo='aceptada@example.org', inscripcion=aceptada)
        InvitacionCurso.objects.create(edicion=grupo, correo='sin-cuenta@example.org')
        with self.assertNumQueries(2):
            resultado = cupos_por_edicion(self.ediciones)
        self.assertEqual(resultado[grupo.pk], 6)
        self.assertEqual(resultado[self.ediciones[1].pk], 8)
        for edicion in self.ediciones:
            self.assertEqual(resultado[edicion.pk], cupos_disponibles(edicion))

    def test_invitaciones_pendientes_sin_exonerar_reservan_una_plaza(self):
        grupo = self.ediciones[0]
        pendiente = InscripcionCurso.objects.create(edicion=grupo, usuario=self.usuario, estado='pendiente')
        invitacion = InvitacionCurso.objects.create(edicion=grupo, correo='pendiente@example.org',
                                                    inscripcion=pendiente, exonerar_matricula=False)
        self.assertEqual(cupos_por_edicion([grupo])[grupo.pk], 7)
        invitacion.activa = False
        invitacion.save(update_fields=['activa'])
        self.assertEqual(cupos_por_edicion([grupo])[grupo.pk], 8)

    def test_grupos_sin_limite_y_lista_vacia_no_consultan_matriculas(self):
        grupo = EdicionCurso.objects.create(curso=self.curso, nombre='Sin límite', anio=2026)
        with self.assertNumQueries(0):
            self.assertEqual(cupos_por_edicion([grupo]), {grupo.pk: None})
            self.assertEqual(cupos_por_edicion([]), {})

    def test_aforo_publico_nunca_es_negativo(self):
        grupo = self.ediciones[0]
        grupo.cupo = 0
        self.assertEqual(cupos_por_edicion([grupo])[grupo.pk], 0)

    def test_oferta_publica_usa_cinco_consultas_con_varios_grupos(self):
        with self.assertNumQueries(5):
            oferta = oferta_publica_para_centros([self.unidad.slug])
        self.assertEqual(len(oferta['cursos']), 1)
        self.assertEqual(len(oferta['cursos'][0]['ediciones']), 12)
        self.assertEqual(oferta['cursos'][0]['ediciones'][0]['cupos'], 8)

    def test_oferta_omite_grupos_inactivos_y_unidades_retiradas(self):
        EdicionCurso.objects.filter(pk=self.ediciones[0].pk).update(activa=False)
        self.assertEqual(len(oferta_publica_para_centros([self.unidad.slug])['cursos'][0]['ediciones']), 11)
        Unidad.objects.filter(pk=self.unidad.pk).update(activo=False)
        self.assertEqual(oferta_publica_para_centros([self.unidad.slug]), {'unidades': [], 'cursos': []})

    def test_cuarenta_grupos_y_mil_doscientas_matriculas_no_aumentan_consultas(self):
        grupos = [EdicionCurso.objects.create(curso=self.curso, nombre=f'Escala {i}', anio=2026, cupo=100)
                  for i in range(40)]
        usuarios = get_user_model().objects.bulk_create([
            get_user_model()(username=f'escala-aforo-{i}') for i in range(1200)])
        InscripcionCurso.objects.bulk_create([
            InscripcionCurso(edicion=grupos[i % 40], usuario=persona, estado='aceptada')
            for i, persona in enumerate(usuarios)])
        with self.assertNumQueries(2):
            cupos = cupos_por_edicion(grupos)
        self.assertEqual(set(cupos.values()), {70})
        with self.assertNumQueries(5):
            oferta = oferta_publica_para_centros([self.unidad.slug])
        self.assertEqual(len(oferta['cursos'][0]['ediciones']), 52)
        self.assertEqual(sum(e['cupos'] == 70 for e in oferta['cursos'][0]['ediciones']), 40)
