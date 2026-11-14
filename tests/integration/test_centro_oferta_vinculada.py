"""Integración de oferta heredada con la ficha pública de centros I+D."""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import cidt
from apps.centros_id.vinculos import oferta_vinculada
from apps.integraciones.unidades import modelo_unidad


class OfertaVinculadaCentroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt).cargar()
        cls.area = cls.centro.componentes.first()
        cls.dia = timezone.localdate() + timedelta(days=2)

    def test_cursos_vinculados_conservan_propietario_edicion_y_url_canonica(self):
        from apps.formacion.models.cursos import Curso, EdicionCurso
        slug = self.area.lista_unidades[0] if self.area.lista_unidades else 'laboratorio-formacion-vinculada'
        self.area.unidades_articuladas = slug
        self.area.save()
        unidad = modelo_unidad().objects.create(nombre='Laboratorio organizador', slug=slug, dependencia='laboratorios',
                                                 fecha_inicio=timezone.localdate())
        curso = Curso.objects.create(unidad=unidad, codigo='FORM-OPER-01', nombre='Curso público vinculado', publicado=True)
        Curso.objects.create(unidad=unidad, codigo='FORM-OCULTO', nombre='Borrador reservado', publicado=False)
        EdicionCurso.objects.create(curso=curso, nombre='Edición abierta', anio=self.dia.year, cupo=4,
            inscripciones_desde=timezone.localdate(), inscripciones_hasta=self.dia, inicio=self.dia,
            fin=self.dia + timedelta(days=5), lugar='Aula de formación vinculada')
        pagina = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'oportunidades']))
        self.assertContains(pagina, curso.nombre)
        self.assertContains(pagina, unidad.nombre)
        self.assertContains(pagina, 'Edición abierta')
        self.assertContains(pagina, 'Aula de formación vinculada')
        self.assertContains(pagina, (self.dia + timedelta(days=5)).strftime('%d/%m/%Y'))
        self.assertNotContains(pagina, 'No hay convocatorias ni oportunidades abiertas.')
        self.assertNotContains(pagina, 'No hay cursos ni convocatorias publicados actualmente.')
        self.assertContains(pagina, reverse('curso_unidad', args=[slug, curso.codigo]))
        self.assertNotContains(pagina, 'Borrador reservado')
        self.assertEqual(Curso.objects.count(), 2)
        with override_settings(CENTROS_ID_UNIT_PROVIDER=''):
            self.assertEqual(oferta_vinculada([slug]), {'unidades': [], 'cursos': []})

    def test_colaboracion_externa_se_identifica_y_no_publica_oferta_desactivada(self):
        from apps.directorio_unidades.selectors import oferta_publica_para_centros
        from apps.formacion.models.cursos import Curso, EdicionCurso

        slug = 'laboratorio-colaboracion-vinculada'
        self.area.unidades_articuladas = slug
        self.area.save()
        unidad = modelo_unidad().objects.create(
            nombre='Laboratorio colaborador UPEC', slug=slug, dependencia='laboratorios',
            fecha_inicio=timezone.localdate(),
        )
        externo = Curso.objects.create(
            unidad=unidad, codigo='FORM-EXT', nombre='Seminario de colaboración tecnológica',
            clasificacion='seminario', origen='externo', publicado=True,
            url_externa='https://formacion.example.org/seminario',
            entidad_organizadora='Instituto colaborador', participacion_unidad='colaborador',
        )
        EdicionCurso.objects.create(curso=externo, nombre='Convocatoria externa', anio=self.dia.year, cupo=10)
        inactivo = Curso.objects.create(
            unidad=unidad, codigo='FORM-INACTIVO', nombre='Actividad retirada del catálogo público',
            publicado=True, activo=False,
        )
        oferta = oferta_publica_para_centros([slug])['cursos']
        self.assertEqual(len(oferta), 1)
        self.assertTrue(oferta[0]['es_externo'])
        self.assertEqual(oferta[0]['organizador'], 'Instituto colaborador')
        self.assertEqual(oferta[0]['url_externa'], externo.url_externa)
        self.assertIsNone(oferta[0]['ediciones'][0]['cupos'])
        pagina = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'oportunidades']))
        for texto in ('Plataforma externa', externo.nombre, 'Instituto colaborador', 'Colaborador:',
                      'Acceder a la plataforma organizadora', externo.url_externa, 'noopener noreferrer'):
            self.assertContains(pagina, texto)
        self.assertNotContains(pagina, inactivo.nombre)
        self.assertNotContains(pagina, '10 cupos libres')
        Curso.objects.filter(pk=externo.pk).update(url_externa='javascript:alert(1)')
        self.assertEqual(oferta_publica_para_centros([slug])['cursos'][0]['url_externa'], '')

    def test_catalogo_vinculado_limita_seis_tarjetas_por_unidad_y_conserva_total_real(self):
        from apps.directorio_unidades.selectors import oferta_publica_para_centros
        from apps.formacion.models.cursos import Curso

        slug = 'laboratorio-catalogo-vinculado-masivo'
        self.area.unidades_articuladas = slug
        self.area.save()
        unidad = modelo_unidad().objects.create(
            nombre='Laboratorio con catálogo amplio', slug=slug, dependencia='laboratorios',
            fecha_inicio=timezone.localdate(),
        )
        Curso.objects.bulk_create([
            Curso(unidad=unidad, codigo=f'OFERTA-{numero:02d}', nombre=f'Actividad de formación {numero:02d}',
                  publicado=True, orden=numero)
            for numero in range(13)
        ])
        Curso.objects.create(unidad=unidad, codigo='OFERTA-OCULTA', nombre='Borrador que no se cuenta')
        Curso.objects.create(unidad=unidad, codigo='OFERTA-RETIRADA', nombre='Inactivo que no se cuenta',
                             publicado=True, activo=False)
        oferta = oferta_publica_para_centros([slug])
        self.assertEqual(len(oferta['cursos']), 6)
        self.assertEqual([curso['nombre'] for curso in oferta['cursos']],
                         [f'Actividad de formación {numero:02d}' for numero in range(6)])
        self.assertEqual(oferta['unidades'][0]['cursos_total'], 13)
        url = reverse('cursos_unidad', args=[slug])
        self.assertEqual(oferta['unidades'][0]['cursos_url'], url)
        pagina = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'oportunidades']))
        self.assertContains(pagina, 'Ver catálogo (13)')
        self.assertContains(pagina, url)
        self.assertNotContains(pagina, 'Actividad de formación 06')
        self.assertNotContains(pagina, 'Borrador que no se cuenta')
        self.assertNotContains(pagina, 'Inactivo que no se cuenta')
