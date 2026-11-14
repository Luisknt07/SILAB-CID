"""Escenario solicitado: contenido completo, relaciones y recorridos sin validaciones institucionales ficticias."""
from datetime import datetime, time, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import cidt
from apps.centros_id.contenidos import Contenidos
from apps.centros_id.escenario_operativo import construir_escenario
from apps.centros_id.formularios import SolicitudForm
from apps.centros_id.investigacion import metadatos, referencias_ris
from apps.centros_id.mapa import MAPA, SUBPAGINAS
from apps.centros_id.models import CentroID, DocumentoCentro, EquipoCentro, HitoProyecto, HorarioRecurso
from apps.centros_id.operaciones import disponibilidad


@override_settings(DEBUG=True, CENTROS_ID_ESCENARIOS_OPERATIVOS=('cidt-upec',))
class EscenarioOperativoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt).cargar()
        construir_escenario(cls.centro)

    def seccion(self, clave):
        return self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, clave]))

    def test_las_seis_pestanas_y_todas_las_secciones_tienen_contenido(self):
        contenidos = Contenidos(self.centro)
        self.assertEqual(self.centro.estado_publico, 'Operativo')
        self.assertEqual(len(contenidos.proyectos), 12)
        self.assertEqual(len(contenidos.resultados), 10)
        self.assertEqual(len(contenidos.casos), 3)
        self.assertEqual(len(contenidos.grupos), 4)
        for clave in MAPA.pestanas:
            with self.subTest(pestana=clave):
                self.assertEqual(self.client.get(reverse('pestana_centro_id', args=[self.centro.slug, clave])).status_code, 200)
        for clave in [*MAPA.secciones, *SUBPAGINAS]:
            with self.subTest(seccion=clave):
                pagina = self.seccion(clave)
                self.assertEqual(pagina.status_code, 200)
                self.assertNotContains(pagina, 'El público no ve este bloque mientras esté vacío.')
        for area in contenidos.areas:
            self.assertEqual(self.client.get(reverse('componente_centro_id', args=[self.centro.slug, area.codigo])).status_code, 200)

    def test_los_proyectos_y_resultados_se_pueden_abrir_y_exportar(self):
        for proyecto in self.centro.proyectos.all():
            self.assertTrue(proyecto.problema and proyecto.objetivos and proyecto.metodologia)
            self.assertEqual(proyecto.hitos_registrados.count(), 4)
            pagina = self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'proyecto', proyecto.pk]))
            self.assertContains(pagina, proyecto.problema)
        for resultado in self.centro.resultados.all():
            self.assertTrue(resultado.archivo and resultado.archivo.storage.exists(resultado.archivo.name))
            self.assertIn('Escenario operativo', metadatos(resultado)['procedencia'])
            self.assertIn('N1  - Escenario operativo', referencias_ris([resultado]))
            self.assertEqual(self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'resultado', resultado.pk])).status_code, 200)
        for catalogo in ('produccion', 'desarrollos'):
            pagina = self.client.get(reverse('exportar_resultados_centro_id', args=[self.centro.slug]), {'catalogo': catalogo})
            self.assertEqual(pagina.status_code, 200)
            self.assertTrue(pagina.json()['total'])

    def test_escenario_no_valida_muestras_ni_expone_documentos_internos(self):
        for relacion in ('proyectos', 'resultados', 'integrantes', 'aliados', 'casos', 'convocatorias', 'novedades', 'grupos', 'documentos'):
            filas = getattr(self.centro, relacion).all()
            self.assertFalse(filas.filter(es_muestra=False).exists())
            self.assertFalse(filas.filter(validado_en__isnull=False).exists())
        interno = DocumentoCentro.objects.create(centro=self.centro, tipo='acta_comite', titulo='Acta interna reservada', publico=False)
        self.assertNotIn(interno, Contenidos(self.centro).documentos)
        self.assertNotContains(self.seccion('gobierno'), interno.titulo)
        otro = CentroID.objects.create(nombre='Otro', slug='otro-escenario')
        self.assertFalse(Contenidos(otro).escenario)

    def test_fuera_del_escenario_las_muestras_y_las_reservas_se_ocultan(self):
        equipo = EquipoCentro.objects.get(componente__centro=self.centro, codigo='CIDT-IA-PR01')
        for ajustes in ({'DEBUG': False}, {'CENTROS_ID_ESCENARIOS_OPERATIVOS': ()}):
            with self.subTest(ajustes=ajustes), override_settings(**ajustes):
                contenidos = Contenidos(self.centro)
                self.assertEqual(self.centro.estado_publico, 'Estado pendiente de validación')
                self.assertEqual(contenidos.proyectos, [])
                self.assertEqual(contenidos.grupos, [])
                self.assertFalse(equipo.apto_reserva)
                self.assertFalse(any(z.es_muestra for z in contenidos.zonas))
                self.assertFalse(any(e.es_muestra for a in contenidos.areas for e in a.equipos.all()))
                self.assertEqual(self.seccion('produccion').status_code, 404)
                self.assertEqual(self.client.get(reverse('fragmento_centro_id', args=[self.centro.slug, 'equipo', equipo.pk])).status_code, 404)

    def test_repetir_la_carga_preserva_ediciones_y_no_duplica_archivos_ni_horarios(self):
        servicio = self.centro.servicios.first()
        servicio.metodo = 'Método editado por el centro'
        servicio.save()
        proyecto = self.centro.proyectos.first()
        proyecto.objetivos = 'Objetivos editados'
        proyecto.save()
        counts = (HitoProyecto.objects.count(), HorarioRecurso.objects.count(), EquipoCentro.objects.count(), self.centro.convocatorias.count())
        archivos = list(self.centro.resultados.values_list('archivo', flat=True))
        call_command('construir_escenario_centros', stdout=StringIO())
        servicio.refresh_from_db()
        proyecto.refresh_from_db()
        self.assertEqual(servicio.metodo, 'Método editado por el centro')
        self.assertEqual(proyecto.objetivos, 'Objetivos editados')
        self.assertEqual(counts, (HitoProyecto.objects.count(), HorarioRecurso.objects.count(), EquipoCentro.objects.count(), self.centro.convocatorias.count()))
        self.assertEqual(archivos, list(self.centro.resultados.values_list('archivo', flat=True)))
        with override_settings(DEBUG=False), self.assertRaises(ValidationError):
            construir_escenario(self.centro)

    def test_cursos_con_programa_y_solicitud_de_participacion(self):
        pagina = self.seccion('oportunidades')
        self.assertEqual(len(pagina.context['cursos_centro']), 4)
        self.assertContains(pagina, 'Modelos, objetivos y límites de un gemelo digital')
        self.assertContains(pagina, 'Solicitar participación', count=4)
        self.assertFalse(any(c.titulo.startswith('Curso: ') for lista in pagina.context['convocatorias'].values() for c in lista))
        self.client.force_login(get_user_model().objects.create_user('participante.escenario'))
        curso = pagina.context['cursos_centro'][0]
        formulario = self.client.get(reverse('seccion_centro_id', args=[self.centro.slug, 'solicitar']),
            {'tipo': 'capacitacion', 'titulo': curso['nombre'], 'area': curso['area']})
        self.assertEqual(formulario.context['formulario'].initial['titulo'], curso['nombre'])

    def test_recursos_con_disponibilidad_y_solicitud_pendiente(self):
        equipo = EquipoCentro.objects.get(componente__centro=self.centro, codigo='CIDT-IA-PR01')
        self.assertTrue(equipo.apto_reserva)
        dia = timezone.localdate() + timedelta(days=1)
        while dia.weekday() > 4:
            dia += timedelta(days=1)
        self.assertTrue(disponibilidad(equipo, dia))
        inicio = timezone.make_aware(datetime.combine(dia, time(10)))
        form = SolicitudForm({'tipo': 'uso', 'perfil': 'interno', 'titulo': 'Práctica de datos', 'problema': 'Preparar el análisis',
            'resultado_esperado': 'Modelo reproducible', 'equipo': equipo.pk, 'inicio_preferido': inicio.isoformat(),
            'fin_preferido': (inicio + timedelta(hours=1)).isoformat(), 'participantes': 1}, centro=self.centro)
        self.assertTrue(form.is_valid(), form.errors)
        solicitud = form.save(commit=False)
        self.assertEqual(solicitud.estado, 'recibida')
        self.assertIsNone(solicitud.inicio_reservado)
        self.assertEqual(solicitud.inicio_preferido, inicio)
        usuario = get_user_model().objects.create_user('reserva.escenario')
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('solicitar_centro_id', args=[self.centro.slug]), form.data)
        self.assertEqual(respuesta.status_code, 302)
        guardada = self.centro.solicitudes.get(usuario=usuario)
        self.assertEqual(guardada.estado, 'recibida')
        self.assertIsNone(guardada.inicio_reservado)

    def test_calculadora_educativa_resuelve_cuello_y_valida_entradas(self):
        url = reverse('simulador_centro_id', args=[self.centro.slug])
        pagina = self.client.get(url)
        self.assertEqual(pagina.context['resultado']['capacidad'], 102)
        self.assertEqual(pagina.context['resultado']['pendientes'], 18)
        self.assertEqual(pagina.context['resultado']['cuello'], 'Ensamble')
        datos = {nombre: campo.initial for nombre, campo in pagina.context['formulario'].fields.items()}
        datos['puestos_ensamble'] = 2
        pagina = self.client.get(url, datos)
        self.assertEqual(pagina.context['resultado']['capacidad'], 136)
        self.assertEqual(pagina.context['resultado']['cuello'], 'Inspección')
        datos['ciclo_ensamble'] = 0
        pagina = self.client.get(url, datos)
        self.assertIsNone(pagina.context['resultado'])
        self.assertIn('ciclo_ensamble', pagina.context['formulario'].errors)
        self.assertContains(self.seccion('recursos'), url)
        with override_settings(DEBUG=False):
            self.assertEqual(self.client.get(url).status_code, 404)
