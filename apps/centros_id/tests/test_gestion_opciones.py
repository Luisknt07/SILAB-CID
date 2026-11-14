"""Catálogos remotos acotados sin recortar la validación ni las selecciones."""
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.centros_id.models import CentroID, Componente, EquipoCentro, HabilitacionEquipo, Integrante, Proyecto
from apps.centros_id.presentation.gestion import _formulario


class GestionOpcionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = get_user_model().objects.create_user('gestor.opciones.qa')
        cls.ajeno = get_user_model().objects.create_user('gestor.ajeno.opciones.qa', is_staff=True)
        cls.inactivo = get_user_model().objects.create_user('usuario.inactivo.opciones.qa', is_active=False)
        cls.centro = CentroID.objects.create(nombre='Opciones QA', slug='opciones-qa', area='digital',
                                             proposito='Pruebas', responsable=cls.gestor)
        cls.otro = CentroID.objects.create(nombre='Otro QA', slug='otro-opciones-qa', area='digital',
                                           proposito='Pruebas', responsable=cls.ajeno)
        Componente.objects.bulk_create([Componente(centro=cls.centro, codigo=f'QA-{i}',
            nombre=f'Capacidad QA {i:03}', tipo='laboratorio') for i in range(105)])
        cls.areas = list(cls.centro.componentes.order_by('pk'))
        cls.area_ajena = Componente.objects.create(centro=cls.otro, codigo='AJENA-QA',
            nombre='Capacidad QA ajena', tipo='laboratorio')
        cls.persona = Integrante.objects.create(centro=cls.centro, nombre='Persona no vigente QA', vigente=False)

    def setUp(self):
        self.client.force_login(self.gestor)

    def opciones(self, **datos):
        return self.client.get(reverse('opciones_gestion_centro_id', args=[self.centro.slug]),
                               {'tipo': 'proyectos.componentes', **datos})

    def editor(self, editar='nuevo', tipo='proyectos', panel='investigacion', fragment=1):
        return reverse('gestion_centro_id', args=[self.centro.slug]) + '?' + urlencode(
            dict(panel=panel, tipo=tipo, editar=editar, fragment=fragment))

    def datos(self, url, **cambios):
        formulario = self.client.get(url).context['formulario']
        datos = {}
        for nombre, campo in formulario.fields.items():
            if getattr(campo.widget, 'input_type', '') == 'file':
                continue
            valor = formulario[nombre].value()
            if isinstance(valor, bool):
                if valor:
                    datos[nombre] = 'on'
            else:
                datos[nombre] = '' if valor is None else valor
        datos.update(cambios)
        return datos

    def test_solo_gestor_del_centro_puede_buscar(self):
        self.client.logout()
        self.assertEqual(self.opciones(q='Capacidad').status_code, 302)
        self.client.force_login(self.ajeno)
        self.assertEqual(self.opciones(q='Capacidad').status_code, 403)
        self.client.force_login(self.gestor)
        url = reverse('opciones_gestion_centro_id', args=[self.otro.slug])
        self.assertEqual(self.client.get(url, {'tipo': 'proyectos.componentes', 'q': 'Capacidad'}).status_code, 403)

    def test_revocacion_de_gestion_se_aplica_con_la_sesion_abierta(self):
        CentroID.objects.filter(pk=self.centro.pk).update(responsable=None)
        self.assertEqual(self.opciones(q='Capacidad').status_code, 403)

    def test_busqueda_pagina_cincuenta_sin_mezclar_centros_ni_bases(self):
        with CaptureQueriesContext(connections['default']) as principales:
            with CaptureQueriesContext(connections[Componente.objects.db]) as locales:
                primera = self.opciones(q='Capacidad').json()
        self.assertEqual((primera['total'], primera['paginas'], len(primera['items'])), (105, 3, 50))
        segunda = self.opciones(q='Capacidad', pagina=2).json()
        tercera = self.opciones(q='Capacidad', pagina=3).json()
        ids = [item['id'] for p in (primera, segunda, tercera) for item in p['items']]
        self.assertEqual(ids, [a.pk for a in self.areas])
        self.assertNotIn(self.area_ajena.pk, ids)
        self.assertLessEqual(len(locales), 12)
        if Componente.objects.db != 'default':
            self.assertLessEqual(len(principales), 6)
            self.assertTrue(all('centros_id_' not in q['sql'] for q in principales))

    def test_consulta_vacia_y_campos_no_declarados_no_enumeran_catalogos(self):
        self.assertEqual(self.opciones().json()['items'], [])
        self.assertEqual(self.opciones(q='C').json()['total'], 0)
        for tipo in ('proyectos.titulo', 'proyectos.centro', 'auth.password', 'inexistente.componentes'):
            with self.subTest(tipo=tipo):
                self.assertEqual(self.opciones(tipo=tipo, q='Capacidad').status_code, 400)

    def test_hidratacion_recupera_ids_fuera_de_primera_pagina_y_rechaza_ajenos(self):
        respuesta = self.opciones(ids=str(self.areas[-1].pk))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['items'], [{'id': self.areas[-1].pk, 'text': str(self.areas[-1])}])
        for ids in (str(self.area_ajena.pk), f'{self.areas[0].pk},{self.area_ajena.pk}', '', '-1',
                    '١', '²', '0', '9223372036854775808', '99999999999999999999', '9' * 5000,
                    ','.join(str(a.pk) for a in self.areas[:51])):
            with self.subTest(ids=ids):
                self.assertEqual(self.opciones(ids=ids).status_code, 400)
        self.assertEqual(self.opciones(q='Capacidad\x00QA').status_code, 400)
        self.assertEqual(self.opciones(q='Capacidad' * 20 + '\x00').status_code, 400)

    def test_paginas_no_validas_y_metodos_no_admitidos(self):
        for pagina in ('0', '-1', 'abc', '99999999999999999999', '4'):
            self.assertEqual(self.opciones(q='Capacidad', pagina=pagina).status_code, 400)
        url = reverse('opciones_gestion_centro_id', args=[self.centro.slug])
        self.assertEqual(self.client.post(url, {}).status_code, 405)
        self.assertEqual(self.client.head(url).status_code, 405)
        respuesta = self.opciones(q='Capacidad')
        self.assertIn('private', respuesta['Cache-Control'])
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')

    def test_editor_nuevo_no_incluye_catalogo_entero_pero_conserva_queryset(self):
        respuesta = self.client.get(self.editor())
        campo = respuesta.context['formulario'].fields['componentes']
        self.assertEqual(campo.queryset.count(), 105)
        self.assertEqual(list(campo.widget.choices), [])
        self.assertNotContains(respuesta, 'Capacidad QA 000')
        self.assertContains(respuesta, 'data-resource-select="proyectos.componentes"')
        completa = self.client.get(self.editor(fragment=0))
        self.assertContains(completa, 'catalogos_busqueda.js')

    def test_editor_conserva_solo_seleccionados_incluidos_no_vigentes_de_su_centro(self):
        proyecto = Proyecto.objects.create(centro=self.centro, titulo='Proyecto QA', resumen='Prueba', responsable=self.persona)
        proyecto.componentes.add(self.areas[-1])
        formulario = self.client.get(self.editor(proyecto.pk)).context['formulario']
        self.assertEqual(list(formulario.fields['componentes'].widget.choices), [(self.areas[-1].pk, str(self.areas[-1]))])
        self.assertIn(self.persona.pk, dict(formulario.fields['responsable'].widget.choices))
        self.assertEqual(formulario.fields['componentes'].queryset.count(), 105)

    def test_post_guarda_sesenta_selecciones_sin_truncar_en_primera_pagina(self):
        url = self.editor()
        elegidas = [a.pk for a in self.areas[-60:]]
        datos = self.datos(url, titulo='Proyecto sin truncar QA', resumen='Resultado esperado QA', componentes=elegidas)
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 302, getattr(respuesta, 'context', None))
        proyecto = Proyecto.objects.get(centro=self.centro, titulo='Proyecto sin truncar QA')
        self.assertEqual(set(proyecto.componentes.values_list('pk', flat=True)), set(elegidas))

    def test_post_ajeno_no_guarda_y_error_conserva_selecciones_validas(self):
        url = self.editor()
        datos = self.datos(url, titulo='', resumen='Prueba', componentes=[self.areas[-1].pk, self.area_ajena.pk])
        respuesta = self.client.post(url, datos)
        formulario = respuesta.context['formulario']
        self.assertIn('componentes', formulario.errors)
        self.assertEqual(list(formulario.fields['componentes'].widget.choices), [(self.areas[-1].pk, str(self.areas[-1]))])
        self.assertEqual(formulario.fields['componentes'].queryset.count(), 105)
        self.assertFalse(Proyecto.objects.filter(centro=self.centro).exists())

    def test_campo_disabled_conserva_original_y_no_ofrece_busqueda(self):
        equipo = EquipoCentro.objects.create(componente=self.areas[0], nombre='Equipo QA')
        formulario = _formulario(EquipoCentro, ['componente', 'nombre'], self.centro, equipo,
            {'componente': self.areas[-1].pk, 'nombre': 'Equipo editado QA'})
        self.assertTrue(formulario.is_valid(), formulario.errors)
        campo = formulario.fields['componente']
        self.assertTrue(campo.disabled)
        self.assertEqual(formulario.cleaned_data['componente'].pk, self.areas[0].pk)
        self.assertNotIn('data-resource-select', campo.widget.attrs)
        self.assertIn(self.areas[0].pk, dict(campo.widget.choices))
        self.assertNotIn(self.areas[-1].pk, dict(campo.widget.choices))

    def test_catalogo_usuarios_mantiene_politica_canonica_activos_sin_credenciales(self):
        equipo = EquipoCentro.objects.create(componente=self.areas[0], nombre='Equipo identidad QA')
        formulario = _formulario(HabilitacionEquipo, ['equipo', 'usuario'], self.centro,
                                 HabilitacionEquipo(equipo=equipo))
        campo = formulario.fields['usuario']
        self.assertEqual(campo.queryset.model, get_user_model())
        respuesta = self.opciones(tipo='habilitaciones.usuario', ids=str(self.gestor.pk))
        self.assertEqual(respuesta.json()['items'], [{'id': self.gestor.pk, 'text': str(self.gestor)}])
        self.assertEqual(self.opciones(tipo='habilitaciones.usuario', ids=str(self.inactivo.pk)).status_code, 400)
        self.assertNotContains(respuesta, 'password')
