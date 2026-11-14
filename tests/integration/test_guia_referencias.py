"""Bibliografía BibTeX → IEEE y materiales complementarios de la guía FT04."""

from tests.integration.utiles import verificar_pertenencia

import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.reservas.presentation.forms import GuiaPracticaForm
from apps.reservas.presentation.guia_referencias import formatear_autores_ieee, formatear_ieee, materiales_a_texto, normalizar_bibliografia, normalizar_materiales_complementarios, parsear_bibtex
from apps.recursos.models.equipos import EquiposServicios
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import GuiaActividadReserva, Reserva
from apps.directorio_unidades.models.core import Unidad
from apps.recursos.models.unidades import UnidadEquipo

ARTICULO = """@article{perez2024,
  author = {P{\\'e}rez, Juan and Garc{\\'i}a, Mar{\\'i}a Jos{\\'e}},
  title = {Determinaci{\\'o}n de acidez en leche comercial},
  journal = {Revista Ecuatoriana de Ciencia},
  volume = {12},
  number = {3},
  pages = {45--58},
  month = mar,
  year = {2024},
  doi = {10.1000/rec.2024.003}
}"""


class FormatoIeeeTests(TestCase):
    def test_articulo_con_acentos_volumen_numero_y_doi(self):
        entradas = parsear_bibtex(ARTICULO)
        self.assertEqual(len(entradas), 1)
        self.assertEqual(entradas[0]['tipo'], 'article')
        self.assertEqual(entradas[0]['clave'], 'perez2024')
        self.assertEqual(
            formatear_ieee(entradas[0]),
            'J. Pérez y M. J. García, “Determinación de acidez en leche comercial,” '
            'Revista Ecuatoriana de Ciencia, vol. 12, n.º 3, pp. 45–58, mar. 2024, '
            'doi: 10.1000/rec.2024.003.',
        )

    def test_libro_ponencia_tesis_y_sitio_web(self):
        libro = parsear_bibtex(
            '@book{skoog, author = {Skoog, Douglas A. and West, Donald M.}, '
            'title = {Fundamentos de química analítica}, edition = {9}, '
            'address = {México}, publisher = {Cengage}, year = {2015}}'
        )[0]
        self.assertEqual(
            formatear_ieee(libro),
            'D. A. Skoog y D. M. West, Fundamentos de química analítica, 9.ª ed. México: Cengage, 2015.',
        )
        ponencia = parsear_bibtex(
            '@inproceedings{c1, author = "Ana Ruiz", title = "Sensores de bajo costo", '
            'booktitle = "Congreso Andino de Instrumentación", address = "Quito, Ecuador", '
            'pages = "10-15", year = 2023}'
        )[0]
        self.assertEqual(
            formatear_ieee(ponencia),
            'A. Ruiz, “Sensores de bajo costo,” en Congreso Andino de Instrumentación, Quito, Ecuador, 2023, pp. 10-15.',
        )
        tesis = parsear_bibtex(
            '@mastersthesis{t1, author = {Luis de la Torre}, title = {Modelado de prototipos}, '
            'school = {Universidad Politécnica Estatal del Carchi}, address = {Tulcán}, year = {2022}}'
        )[0]
        self.assertEqual(
            formatear_ieee(tesis),
            'L. de la Torre, “Modelado de prototipos,” Tesis de maestría, '
            'Universidad Politécnica Estatal del Carchi, Tulcán, 2022.',
        )
        web = parsear_bibtex(
            '@online{w1, author = {{Organización Mundial de la Salud}}, title = {Bioseguridad en el laboratorio}, '
            'url = {https://www.who.int/es/bioseguridad}, urldate = {2026-09-05}, year = {2020}}'
        )[0]
        self.assertEqual(
            formatear_ieee(web),
            'Organización Mundial de la Salud, “Bioseguridad en el laboratorio,” 2020. [En línea]. '
            'Disponible en: https://www.who.int/es/bioseguridad (accedido: 2026-09-05)',
        )

    def test_autores_multiples_y_et_al(self):
        self.assertEqual(formatear_autores_ieee('Ana Ruiz and Beltrán, Carlos and Diana Mora'), 'A. Ruiz, C. Beltrán y D. Mora')
        siete = ' and '.join(f'Autor{i}, Nombre' for i in range(7))
        self.assertEqual(formatear_autores_ieee(siete), 'N. Autor0 et al.')
        self.assertEqual(formatear_autores_ieee('Jean-Pierre Dupont'), 'J.-P. Dupont')

    def test_texto_mixto_conserva_lineas_sueltas_sin_numeracion(self):
        texto = '[1] Norma NTE INEN 9:2012. Leche cruda. Requisitos.\n' + ARTICULO + '\n\n2. Manual del equipo, versión 3.'
        referencias = normalizar_bibliografia(texto)
        self.assertEqual(len(referencias), 3)
        self.assertEqual(referencias[0], 'Norma NTE INEN 9:2012. Leche cruda. Requisitos.')
        self.assertTrue(referencias[1].startswith('J. Pérez y M. J. García'))
        self.assertEqual(referencias[2], 'Manual del equipo, versión 3.')
        self.assertEqual(normalizar_bibliografia(''), [])

    def test_materiales_complementarios(self):
        materiales = normalizar_materiales_complementarios(
            'Video de tinción de Gram | https://youtu.be/abc123\n'
            'https://datos.upec.edu.ec/leche.csv\n'
            'Lectura previa (capítulo 4)\n'
            'Sitio inseguro | ftp://viejo'
        )
        self.assertEqual(materiales, [
            {'titulo': 'Video de tinción de Gram', 'url': 'https://youtu.be/abc123'},
            {'titulo': 'datos.upec.edu.ec', 'url': 'https://datos.upec.edu.ec/leche.csv'},
            {'titulo': 'Lectura previa (capítulo 4)', 'url': ''},
            {'titulo': 'Sitio inseguro | ftp://viejo', 'url': ''},
        ])
        self.assertEqual(
            materiales_a_texto(materiales[:2]),
            'Video de tinción de Gram | https://youtu.be/abc123\ndatos.upec.edu.ec | https://datos.upec.edu.ec/leche.csv',
        )


class ReferenciasEnLaGuiaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.docente = User.objects.create_user(
            'docente-referencias', password='clave-segura',
            email='referencias@upec.edu.ec', first_name='Docente', last_name='Referencias',
        )
        perfil = cls.docente.profile
        perfil.tipo_usuario = 'docente'
        perfil.facultad = 'agropecuarias_ambientales'
        perfil.carrera = 'computacion'
        perfil.institucion = 'UPEC'
        perfil.save()
        verificar_pertenencia(cls.docente)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de referencias',
            descripcion='Unidad para validar la bibliografía IEEE.',
            fecha_inicio=date(2026, 1, 1),
            dependencia='laboratorios',
            slug='laboratorio-referencias',
        )
        catalogo = EquiposServicios.objects.create(codigo='EQ-REF-001', nombre='Potenciómetro')
        cls.equipo = UnidadEquipo.objects.create(
            codigo_unidad='UE-REF-001', equipo=catalogo, laboratorio=cls.unidad,
            estado_unidad='disponible', activa=True,
        )
        cls.area = EspacioReservable.objects.create(
            unidad=cls.unidad, codigo='AREA-REF', nombre='Área de análisis',
            tipo='area', politica_reserva='tecnico', capacidad=8, reservable=True, activo=True,
        )
        cls.area.equipos_asociados.add(cls.equipo)

    def setUp(self):
        self.client.force_login(self.docente)

    def _crear_guia(self):
        respuesta = self.client.post(reverse('crear_reserva'), {
            'unidad_id': self.unidad.pk,
            'tipo_solicitud': 'recursos',
            'fecha_inicio': '2026-11-19T09:00',
            'fecha_fin': '2026-11-19T11:00',
            'horas_seleccionadas': json.dumps([9, 10]),
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'alcance_beneficiario': 'perfil_solicitante',
            'vinculacion_actividad': 'manual',
            'referencia_actividad': 'Valoración ácido-base mediante potenciómetro',
            'origen_programacion': 'adicional',
            'participantes_seleccionados': '[]',
            'aceptar_terminos': 'on',
            'incluye_espacio': 'true',
            'solicito_espacio': 'true',
            'solicito_equipo': 'true',
            'alcance_espacio': 'areas',
            'espacios_solicitados': [str(self.area.pk)],
            'unidades_seleccionadas': json.dumps([{'id': self.equipo.pk}]),
            'provision_consumibles': 'ninguno',
            'guia_confirmada_solicitante': '1',
            'guia_asignatura': 'Química Analítica',
            'guia_resultado_aprendizaje': 'Determina la acidez de una muestra con precisión.',
            'guia_objetivos': 'Calibrar el potenciómetro.\nTitular la muestra.',
            'guia_formato_procedimiento': 'numerado',
            'guia_procedimiento': 'Calibrar\nMedir\nRegistrar',
            'guia_bibliografia': ARTICULO + '\nNorma NTE INEN 9:2012. Leche cruda. Requisitos.',
            'guia_materiales_complementarios': 'Video de calibración | https://youtu.be/abc123\nHoja de datos del potenciómetro',
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        return GuiaActividadReserva.objects.get(actividad=reserva.actividad_catalogo, es_estructurada=True)

    def test_la_guia_guarda_ieee_conserva_la_fuente_y_enlaza_materiales(self):
        guia = self._crear_guia()
        contenido = guia.contenido
        self.assertTrue(contenido['bibliografia'][0].startswith('J. Pérez y M. J. García, “Determinación'))
        self.assertEqual(contenido['bibliografia'][1], 'Norma NTE INEN 9:2012. Leche cruda. Requisitos.')
        self.assertIn('@article{perez2024', contenido['bibliografia_fuente'])
        self.assertEqual(contenido['materiales_complementarios'], [
            {'titulo': 'Video de calibración', 'url': 'https://youtu.be/abc123'},
            {'titulo': 'Hoja de datos del potenciómetro', 'url': ''},
        ])

        vista = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]))
        self.assertEqual(vista.status_code, 200)
        self.assertContains(vista, '<ol class="guide-references">')
        self.assertContains(vista, 'J. Pérez y M. J. García')
        self.assertContains(vista, 'href="https://youtu.be/abc123"')
        self.assertContains(vista, 'Materiales complementarios')

        pdf = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]) + '?preview=pdf')
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))

        # El editor vuelve a mostrar la fuente BibTeX y los materiales editables.
        form = GuiaPracticaForm(unidad=self.unidad, usuario=self.docente, guia=guia)
        self.assertIn('@article{perez2024', form.initial['bibliografia'])
        self.assertEqual(
            form.initial['materiales_complementarios'],
            'Video de calibración | https://youtu.be/abc123\nHoja de datos del potenciómetro',
        )

    def test_el_formateador_para_la_vista_previa_exige_sesion(self):
        url = reverse('formatear_bibliografia_guia')
        self.client.logout()
        anonimo = self.client.post(url, data=json.dumps({'texto': ARTICULO}), content_type='application/json')
        self.assertIn(anonimo.status_code, (302, 403))

        self.client.force_login(self.docente)
        respuesta = self.client.post(
            url,
            data=json.dumps({'texto': ARTICULO, 'materiales': 'Guía rápida | https://upec.edu.ec/guia'}),
            content_type='application/json',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        datos = respuesta.json()
        self.assertTrue(datos['referencias'][0].startswith('J. Pérez y M. J. García'))
        self.assertEqual(datos['materiales'], [{'titulo': 'Guía rápida', 'url': 'https://upec.edu.ec/guia'}])

        invalido = self.client.post(url, data='no-json', content_type='application/json')
        self.assertEqual(invalido.status_code, 400)
