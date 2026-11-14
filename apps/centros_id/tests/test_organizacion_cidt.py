"""Organización pública, aislamiento y actualización sin pérdida de ediciones."""
from io import StringIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import router
from django.test import TestCase
from django.urls import reverse

from apps.centros_id.carga import Cargador
from apps.centros_id.contenido import cidt
from apps.centros_id.contenidos import Contenidos
from apps.centros_id.models import CentroID, Componente, Proyecto, Resultado


class OrganizacionCIDTTests(TestCase):
    databases = {'default', 'centros'} if getattr(settings, 'CENTROS_DB_ENABLED', False) else {'default'}

    @classmethod
    def setUpTestData(cls):
        cls.centro = Cargador(cidt).cargar()

    def test_jerarquia_conserva_nueve_fichas_y_no_duplica_comercio(self):
        c = Contenidos(self.centro)
        self.assertEqual(len(c.areas), 9)
        self.assertEqual([len(areas) for _, areas in c.areas_por_tipo()], [5, 2, 1])
        cedi = next(a for a in c.areas if a.codigo == 'smart-cedi')
        self.assertEqual([a.codigo for a in c.modulos_de(cedi)], ['comercio-exterior'])
        with self.assertNumQueries(0, using=router.db_for_read(CentroID)):
            botones, _ = c._contenido('areas')
        integrado = next(b for b in botones if b['id'] == 'area-comercio-exterior')
        self.assertTrue(integrado['integrado'])
        self.assertEqual(integrado['contenedor'], 'Smart CEDI')
        self.assertEqual(sum(b['id'] == integrado['id'] for b in botones), 1)

    def test_rechaza_otro_centro_autorreferencia_y_modulos_anidados(self):
        cedi = self.centro.componentes.get(codigo='smart-cedi')
        modulo = self.centro.componentes.get(codigo='comercio-exterior')
        otro = CentroID.objects.create(nombre='Otro centro', slug='otro-centro', area='digitales')
        area = Componente(centro=otro, nombre='Área externa', codigo='externa', tipo='modulo',
                          resumen='Resumen', descripcion='Descripción', integrado_en=cedi)
        with self.assertRaises(ValidationError):
            area.full_clean()
        cedi.integrado_en = cedi
        with self.assertRaises(ValidationError):
            cedi.full_clean()
        cedi.integrado_en = modulo
        with self.assertRaises(ValidationError):
            cedi.full_clean()
        nueva = Componente(centro=self.centro, nombre='Submódulo', codigo='submodulo', tipo='modulo',
                          resumen='Resumen', descripcion='Descripción', integrado_en=modulo)
        with self.assertRaises(ValidationError):
            nueva.full_clean()

    def test_nueve_areas_tienen_operacion_materiales_y_actividades_de_16_carreras(self):
        carreras = set()
        for area in self.centro.componentes.all():
            self.assertTrue(area.sectores_operativos)
            self.assertTrue(area.lista_insumos)
            self.assertTrue(area.aplicaciones_academicas)
            carreras.update(f[0] for f in area.aplicaciones_academicas)
        self.assertEqual(len(carreras), 16)
        self.assertEqual(carreras, set(self.centro.articulaciones.filter(tipo='carrera').values_list('actor', flat=True)))

    def test_area_muestra_modulo_y_actividad_y_comercio_regresa_al_cedi(self):
        respuesta = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'smart-cedi']))
        self.assertContains(respuesta, 'Módulos integrados')
        self.assertContains(respuesta, 'Cuarentena y control de entrada')
        self.assertContains(respuesta, 'Qué hace cada carrera aquí')
        self.assertContains(respuesta, 'Insumos y materiales')
        respuesta = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, 'comercio-exterior']))
        self.assertContains(respuesta, 'Módulo integrado en')
        self.assertEqual(respuesta.context['integrado_en'].codigo, 'smart-cedi')

    def test_resultado_compartido_se_muestra_sin_duplicar_el_registro(self):
        factory = self.centro.componentes.get(codigo='smart-factory')
        cedi = self.centro.componentes.get(codigo='smart-cedi')
        proyecto = Proyecto.objects.create(centro=self.centro, titulo='Proyecto compartido', publicado=True)
        proyecto.componentes.add(factory, cedi)
        resultado = Resultado.objects.create(centro=self.centro, titulo='Resultado único', tipo='dato',
            anio=2026, componente=factory, proyecto=proyecto, publicado=True)
        Resultado.objects.create(centro=self.centro, titulo='Resultado privado', tipo='dato',
            anio=2026, componente=factory, proyecto=proyecto, publicado=True, confidencial=True)
        respuesta = self.client.get(reverse('componente_centro_id', args=[self.centro.slug, cedi.codigo]))
        self.assertEqual([r.pk for r in respuesta.context['resultados']], [resultado.pk])
        self.assertEqual(self.centro.resultados.filter(titulo='Resultado único').count(), 1)

    def test_actualizacion_reconoce_precarga_preserva_manual_y_es_idempotente(self):
        cedi = self.centro.componentes.get(codigo='smart-cedi')
        datos = cidt.REVISION_ORGANIZACION['componentes']['smart-cedi']
        cedi.descripcion = datos['antes']['descripcion']
        cedi.capacidades = 'Capacidad editada por el gestor'
        cedi.organizacion_operativa = ''
        cedi.save()
        anterior_pk = cedi.pk
        salida = StringIO()
        call_command('actualizar_organizacion_cidt', stdout=salida)
        cedi.refresh_from_db()
        self.assertEqual(cedi.descripcion, datos['antes']['descripcion'])
        self.assertEqual(cedi.organizacion_operativa, '')
        call_command('actualizar_organizacion_cidt', aplicar=True, stdout=StringIO())
        cedi.refresh_from_db()
        self.assertEqual(cedi.pk, anterior_pk)
        self.assertEqual(cedi.descripcion, datos['despues']['descripcion'])
        self.assertEqual(cedi.capacidades, 'Capacidad editada por el gestor')
        self.assertTrue(cedi.organizacion_operativa)
        conteos = (self.centro.componentes.count(), self.centro.servicios.count(), self.centro.articulaciones.count())
        salida = StringIO()
        call_command('actualizar_organizacion_cidt', aplicar=True, stdout=salida)
        self.assertIn('0 registros', salida.getvalue())
        self.assertEqual(conteos, (self.centro.componentes.count(), self.centro.servicios.count(), self.centro.articulaciones.count()))

    def test_actualizar_gobierno_y_modulo_preserva_identificadores_y_ediciones_de_pasos(self):
        datos = cidt.REVISION_ORGANIZACION['gobierno'][0]
        oficina = self.centro.gobierno.get(nombre=datos['despues'][0])
        oficina.nombre = datos['antes'][0]
        oficina.save()
        modulo = self.centro.componentes.get(codigo='comercio-exterior')
        modulo.integrado_en = None
        modulo.save()
        cedi = self.centro.componentes.get(codigo='smart-cedi')
        paso = cedi.procesos.first().pasos.first()
        paso.descripcion = 'Instrucción técnica escrita por el responsable'
        paso.save()
        ids = (oficina.pk, modulo.pk, paso.pk)
        call_command('actualizar_organizacion_cidt', aplicar=True, stdout=StringIO())
        oficina.refresh_from_db()
        modulo.refresh_from_db()
        paso.refresh_from_db()
        self.assertEqual((oficina.pk, modulo.pk, paso.pk), ids)
        self.assertEqual(oficina.nombre, datos['despues'][0])
        self.assertEqual(modulo.integrado_en_id, cedi.pk)
        self.assertEqual(paso.descripcion, 'Instrucción técnica escrita por el responsable')

    def test_actualiza_solo_categorias_heredadas_y_conserva_clasificacion_manual(self):
        equipos = list(self.centro.componentes.get(codigo='ia-datos').equipos.all()[:2])
        equipos[0].categoria = 'División tecnológica'
        equipos[1].categoria = 'Clasificación técnica del gestor'
        for equipo in equipos:
            equipo.save(update_fields=['categoria'])
        call_command('actualizar_organizacion_cidt', aplicar=True, stdout=StringIO())
        for equipo in equipos:
            equipo.refresh_from_db()
        self.assertEqual(equipos[0].categoria, 'Área de tecnología aplicada')
        self.assertEqual(equipos[1].categoria, 'Clasificación técnica del gestor')

    def test_completa_servicios_transversales_sin_cambiar_texto_manual_ni_precio(self):
        servicio = self.centro.servicios.get(nombre='Evaluación de impacto')
        servicio.metodo = ''
        servicio.alcance = 'Alcance acordado por el gestor'
        servicio.save()
        call_command('actualizar_organizacion_cidt', aplicar=True, stdout=StringIO())
        servicio.refresh_from_db()
        self.assertEqual(servicio.alcance, 'Alcance acordado por el gestor')
        self.assertIn('línea base', servicio.metodo)
        self.assertFalse(servicio.tarifa)
        self.assertEqual(servicio.estado_oferta, 'consultar')
