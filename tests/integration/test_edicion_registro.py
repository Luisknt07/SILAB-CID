"""Editar en la propia página lo que muestra el visualizador: cada página ofrece «Editar» y «Agregar» solo a quien
tiene el permiso de la unidad para esa parte, y el cuadro guarda sin salir de la página."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.recursos.models.consumibles import Consumible
from apps.recursos.models.equipos import EquiposServicios
from apps.plantas_piloto.operacion.models.produccion import EtapaReceta, Producto, Receta
from apps.gestion_unidades.models.novedades import NovedadUnidad
from apps.gestion_unidades.models.presentacion import PresentacionUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class EdicionEnLaPaginaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.coordinador = User.objects.create_user('coordina-registro', password='clave')
        identificar(cls.coordinador, tipo_usuario='administrativo', carrera='')
        cls.visitante = User.objects.create_user('visita-registro', password='clave')
        identificar(cls.visitante, tipo_usuario='estudiante')
        cls.lab = Unidad.objects.create(nombre='Laboratorio editable en página', slug='lab-editable-pagina',
                                        dependencia='laboratorios', descripcion='.', fecha_inicio=date(2026, 1, 1),
                                        administrador=cls.coordinador)
        cls.unity = SoftwareDisponible.objects.create(unidad=cls.lab, nombre='Unity', licencias_totales=5,
                                                      licencias_disponibles=5)
        cls.producto = Producto.objects.create(unidad=cls.lab, codigo='REG-APP', nombre='Aplicación', unidad_medida='aplicación',
                                               publico=True)
        cls.proceso = Receta.objects.create(unidad=cls.lab, producto=cls.producto, codigo='REG-PRO', nombre='Desarrollo',
                                            cantidad_base=1, unidad_base='aplicación', rendimiento_esperado=100, activa=True)
        cls.etapa = EtapaReceta.objects.create(receta=cls.proceso, orden=1, nombre='Guion', instrucciones='Escribir el guion.')

    def setUp(self):
        self.client.force_login(self.coordinador)

    def url(self, clave, pk, **parametros):
        base = reverse('editar_registro', args=[self.lab.slug, clave, pk])
        return base + ('?' + '&'.join(f'{k}={v}' for k, v in parametros.items()) if parametros else '')

    def guardar(self, clave, pk, datos, **parametros):
        return self.client.post(self.url(clave, pk, **parametros), {f'registro-{k}': v for k, v in datos.items()},
                                HTTP_X_REQUESTED_WITH='fetch')

    def test_las_paginas_ofrecen_editar_solo_a_quien_puede(self):
        paginas = {
            'software_unidad': self.url('software', self.unity.pk), 'productos_laboratorio': self.url('producto', 'nuevo'),
            'conoce_unidad': self.url('presentacion', 'unidad', grupo='quienes'),
            'ficha_unidad': self.url('unidad', 'unidad', grupo='identidad'),
            'novedades_unidad': self.url('novedad', 'nuevo'), 'insumos_unidad': self.url('insumo', 'nuevo'),
        }
        for nombre, enlace in paginas.items():
            with self.subTest(pagina=nombre):
                pagina = self.client.get(reverse(nombre, args=[self.lab.slug])).content.decode()
                self.assertIn(enlace.replace('&', '&amp;'), pagina)
                self.assertIn('edicion_en_ficha.js', pagina)
        proceso = self.client.get(reverse('proceso_laboratorio', args=[self.lab.slug, self.proceso.pk]))
        self.assertContains(proceso, self.url('etapa', self.etapa.pk))
        self.assertContains(proceso, self.url('etapa', 'nuevo', padre=self.proceso.pk))
        self.assertNotContains(proceso, 'admin/laboratorios/receta')
        self.client.force_login(self.visitante)
        self.assertNotContains(self.client.get(reverse('software_unidad', args=[self.lab.slug])), 'data-editar-ficha')
        self.assertEqual(self.client.get(self.url('software', self.unity.pk)).status_code, 403)

    def test_editar_crear_y_eliminar_desde_el_cuadro(self):
        formulario = self.client.get(self.url('software', self.unity.pk), {'fragmento': '1'})
        self.assertContains(formulario, 'name="registro-nombre"')
        self.assertNotContains(formulario, '<html')
        self.assertEqual(self.guardar('software', self.unity.pk, {
            'nombre': 'Unity 6', 'tipo_recurso': self.unity.tipo_recurso, 'tipo_acceso': self.unity.tipo_acceso,
            'uso_en_equipo': self.unity.uso_en_equipo, 'licencias_totales': 5, 'licencias_disponibles': 4,
            'activo': 'on'}).json(), {'ok': True})
        self.unity.refresh_from_db()
        self.assertEqual((self.unity.nombre, self.unity.licencias_disponibles), ('Unity 6', 4))
        # Una etapa nueva nace en su proceso, al final.
        self.guardar('etapa', 'nuevo', {'orden': 2, 'nombre': 'Publicar', 'personas': 1, 'duracion_min': 30, 'tipo': self.etapa.tipo},
                     padre=self.proceso.pk)
        self.assertEqual(list(self.proceso.etapas.order_by('orden').values_list('nombre', flat=True)), ['Guion', 'Publicar'])
        nueva = self.proceso.etapas.get(nombre='Publicar')
        self.guardar('etapa', nueva.pk, {'orden': 2, 'nombre': 'Publicar', 'personas': 1, 'duracion_min': 30,
                                         'tipo': nueva.tipo, 'eliminar': 'on'})
        self.assertFalse(EtapaReceta.objects.filter(pk=nueva.pk).exists())
        self.guardar('insumo', 'nuevo', {'nombre': 'Máscaras desechables', 'codigo': 'REG-MASC',
                                         'clasificacion': 'insumo', 'cantidad_por_presentacion': 1,
                                         'unidad_medida': 'u', 'activo': 'on'})
        self.assertTrue(Consumible.objects.filter(unidad=self.lab, codigo='REG-MASC').exists())
        self.guardar('novedad', 'nuevo', {'titulo': 'Casa abierta', 'resumen': 'Visítanos.', 'categoria': 'noticia',
                                          'fecha_publicacion': '2026-10-03',
                                          'publicada': 'on'})
        self.assertTrue(NovedadUnidad.objects.filter(unidad=self.lab, titulo='Casa abierta').exists())

    def test_los_registros_unicos_se_editan_por_partes(self):
        self.guardar('presentacion', 'unidad', {'que_es': 'Un laboratorio de realidad extendida.', 'publicada': 'on'},
                     grupo='quienes')
        presentacion = PresentacionUnidad.objects.get(unidad=self.lab)
        self.assertEqual((presentacion.que_es, presentacion.publicada), ('Un laboratorio de realidad extendida.', True))
        self.guardar('presentacion', 'unidad', {'mision': 'Formar con tecnología inmersiva.'}, grupo='rumbo')
        presentacion.refresh_from_db()
        self.assertEqual((presentacion.que_es, presentacion.mision),
                         ('Un laboratorio de realidad extendida.', 'Formar con tecnología inmersiva.'))
        self.guardar('unidad', 'unidad', {'telefono': '(06) 2980 302', 'contacto_email': 'lab@example.org'},
                     grupo='atencion')
        self.lab.refresh_from_db()
        self.assertEqual((self.lab.telefono, self.lab.nombre), ('(06) 2980 302', 'Laboratorio editable en página'))

    def test_el_rol_del_personal_no_se_cambia_desde_la_pagina(self):
        persona = ResponsableUnidad.objects.create(unidad=self.lab, nombre='Técnica', rol='responsable_tecnico',
                                                   publico=True, activo=True)
        self.assertContains(self.client.get(reverse('ficha_unidad', args=[self.lab.slug])), self.url('responsable', persona.pk))
        formulario = self.client.get(self.url('responsable', persona.pk), {'fragmento': '1'})
        self.assertNotContains(formulario, 'name="registro-rol"')
        self.client.post(self.url('responsable', persona.pk), {'registro-nombre': 'Técnica XR', 'registro-rol': 'coordinacion',
                                                              'registro-email': 'tecnica@example.org', 'registro-publico': 'on',
                                                              'registro-orden': 1})
        persona.refresh_from_db()
        self.assertEqual((persona.nombre, persona.rol), ('Técnica XR', 'responsable_tecnico'))
        self.assertEqual(self.client.get(self.url('responsable', 'nuevo')).status_code, 404)
        self.assertEqual(self.client.get(self.url('equipo', 1)).status_code, 404)
        self.assertFalse(EquiposServicios.objects.exists())
