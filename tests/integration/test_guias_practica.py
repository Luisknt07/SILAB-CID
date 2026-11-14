
from tests.integration.utiles import verificar_pertenencia
from datetime import date, time
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.reservas.presentation.guia_firmas import verificar_firma_elaborador

from apps.reservas.models.reservas import CatalogoActividadReserva, GuiaActividadReserva, Reserva
from apps.formacion.models.practicas import PlanificacionPractica, RegistroAuditoriaUnidad
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.recursos.models.software import SoftwareDisponible
from apps.directorio_unidades.models.core import Unidad


class GuiaPracticaEstructuradaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.autor = User.objects.create_user('autor-guia', password='clave-segura')
        cls.autor.profile.tipo_usuario = 'docente'
        cls.autor.profile.facultad = 'agropecuarias_ambientales'
        cls.autor.profile.carrera = 'computacion'
        cls.autor.profile.institucion = 'UPEC'
        cls.autor.profile.save()
        verificar_pertenencia(cls.autor)
        cls.revisor = User.objects.create_user('revisor-guia', password='clave-segura')
        cls.ajeno = User.objects.create_user('ajeno-guia', password='clave-segura')
        cls.ajeno.profile.tipo_usuario = 'estudiante'
        cls.ajeno.profile.facultad = 'agropecuarias_ambientales'
        cls.ajeno.profile.carrera = 'computacion'
        cls.ajeno.profile.nivel_academico = 'quinto_semestre'
        cls.ajeno.profile.cedula = 'GUIA-EST-001'
        cls.ajeno.profile.institucion = 'UPEC'
        cls.ajeno.profile.save()
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio de guías estructuradas',
            slug='laboratorio-guias-estructuradas',
            dependencia='laboratorios',
            descripcion='Unidad para validar el flujo documental.',
            fecha_inicio=date(2026, 1, 1),
            administrador=cls.revisor,
        )

    @staticmethod
    def lineas(valor):
        """Apartados como ``medidas_seguridad`` se guardan en texto plano."""
        if isinstance(valor, (list, tuple)):
            return [str(item).strip() for item in valor if str(item).strip()]
        return [linea.strip() for linea in str(valor or '').splitlines() if linea.strip()]

    def datos_completos(self, **overrides):
        data = {
            'proposito_codigo': 'docencia_practica',
            'subtipo_actividad': 'practica_curricular',
            'nombre_actividad': 'Práctica de manufactura digital',
            'codigo_actividad': 'ACT-CAD-01',
            'descripcion_actividad': 'Aplicación práctica en el laboratorio.',
            'titulo': 'Guía de práctica de modelado CAD',
            'codigo_guia': 'GUIA-CAD-01',
            'asignatura': 'Diseño asistido por computador',
            'carrera_semestre': 'Logística y Transporte · sexto semestre',
            'docente_responsable': 'Ing. Docente Responsable',
            'categoria_uso': 'Docencia y práctica curricular',
            'duracion': '2 horas',
            'maximo_estudiantes': '20',
            'resultado_aprendizaje': 'Modela una pieza aplicando restricciones dimensionales.',
            'objetivos': 'Construir un modelo bidimensional verificable.',
            'fundamento_teorico': 'Principios de geometría paramétrica y normalización técnica.',
            'equipos': 'Estación CAD\nProyector',
            'materiales': 'Hoja de trabajo\nArchivo base',
            'reactivos': '',
            'medidas_seguridad': 'Aplicar ergonomía y mantener libre el puesto de trabajo.',
            'formato_procedimiento': 'numerado',
            'procedimiento': 'Abrir el archivo base\nCrear el croquis\nValidar dimensiones',
            'resultados_esperados': 'Modelo terminado y validado.',
            'criterios_evaluacion': 'Precisión dimensional, orden y entrega.',
            'manejo_residuos': 'No aplica.',
            'bibliografia': 'ISO 128. Dibujos técnicos.\nManual de la herramienta CAD.',
            'permite_descarga': 'on',
            'accion': 'enviar_revision',
        }
        data.update(overrides)
        return data

    def test_crea_borrador_sobre_actividad_nueva(self):
        self.client.force_login(self.autor)
        response = self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]),
            self.datos_completos(accion='guardar'),
        )

        self.assertEqual(response.status_code, 302)
        guia = GuiaActividadReserva.objects.get()
        self.assertTrue(guia.es_estructurada)
        self.assertEqual(guia.estado_publicacion, 'borrador')
        self.assertEqual(guia.actividad.creado_por, self.autor)
        self.assertEqual(guia.contenido['procedimiento'][0], 'Abrir el archivo base')
        self.assertEqual(guia.contenido['formato_procedimiento'], 'numerado')
        self.assertFalse(bool(guia.archivo))

    def test_estudiante_no_puede_crear_una_guia(self):
        self.client.force_login(self.ajeno)
        response = self.client.get(
            reverse('nueva_guia_practica', args=[self.unidad.slug])
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            'Para crear guías nuevas necesitas verificación docente vigente',
            status_code=403,
        )

    def test_alta_revalida_autorizacion_antes_de_crear_actividad_o_guia(self):
        from unittest.mock import patch

        self.client.force_login(self.autor)
        guias = GuiaActividadReserva.objects.count()
        actividades = CatalogoActividadReserva.objects.count()
        with patch('apps.reservas.presentation.guias._puede_crear_guias',
                   side_effect=[True, False]):
            respuesta = self.client.post(
                reverse('nueva_guia_practica', args=[self.unidad.slug]),
                self.datos_completos(accion='guardar'),
            )
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(GuiaActividadReserva.objects.count(), guias)
        self.assertEqual(CatalogoActividadReserva.objects.count(), actividades)

    def test_procedimiento_admite_vinetas_o_parrafos_sin_duplicar_marcadores(self):
        self.client.force_login(self.autor)
        response = self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]),
            self.datos_completos(
                accion='guardar',
                formato_procedimiento='vinetas',
                procedimiento='- Preparar el equipo\n• Ejecutar la prueba\n3. Registrar el resultado',
            ),
        )
        self.assertEqual(response.status_code, 302, response.content)
        guia = GuiaActividadReserva.objects.get()
        self.assertEqual(guia.contenido['formato_procedimiento'], 'vinetas')
        self.assertEqual(
            guia.contenido['procedimiento'],
            ['Preparar el equipo', 'Ejecutar la prueba', 'Registrar el resultado'],
        )

        guia.estado_publicacion = 'borrador'
        guia.save(update_fields=['estado_publicacion'])
        response = self.client.post(
            reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk]),
            self.datos_completos(
                actividad_existente=str(guia.actividad_id),
                accion='guardar',
                formato_procedimiento='parrafos',
                procedimiento=(
                    'Primero se contextualiza la actividad y se verifican los recursos.\n\n'
                    'Luego se ejecuta el trabajo y se documentan los resultados.'
                ),
            ),
        )
        self.assertEqual(response.status_code, 302, response.content)
        guia.refresh_from_db()
        self.assertEqual(guia.contenido['formato_procedimiento'], 'parrafos')
        self.assertEqual(len(guia.contenido['procedimiento']), 2)

    def test_autocompleta_desde_una_reserva_identificada_y_conserva_su_origen(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Práctica de impresión FDM',
            codigo='FDM-01',
            unidad=self.unidad,
            responsable='Docente FDM',
            creado_por=self.autor,
            estado_publicacion='borrador',
            visibilidad='privada',
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            actividad_catalogo=actividad,
            usuario=self.autor,
            fecha=date(2026, 9, 15),
            hora_inicio=time(8),
            hora_fin=time(10, 30),
            equipo_codigo='FDM-01',
            equipo_nombre='Impresora 3D FDM',
            unidades_seleccionadas=json.dumps([
                {'codigo': 'FAB-UNIT-FDM-01', 'nombre': 'Impresora 3D FDM'}
            ]),
            proposito_codigo='docencia_practica',
            vinculacion_actividad='catalogo',
            referencia_actividad='Manufactura aditiva',
            responsable_actividad='Docente FDM',
            numero_participantes=18,
        )
        software = SoftwareDisponible.objects.create(
            unidad=self.unidad,
            nombre='Ultimaker Cura',
            version='5',
            tipo_acceso='red',
        )
        reserva.software_solicitado.add(software)
        self.client.force_login(self.autor)
        response = self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]),
            self.datos_completos(
                actividad_existente=str(actividad.pk),
                reserva_referencia=str(reserva.pk),
                titulo='',
                codigo_guia='',
                asignatura='',
                docente_responsable='',
                categoria_uso='',
                duracion='',
                maximo_estudiantes='',
                equipos='',
                accion='guardar',
            ),
        )
        self.assertEqual(response.status_code, 302, response.content)
        guia = GuiaActividadReserva.objects.get(actividad=actividad, es_estructurada=True)
        self.assertEqual(guia.titulo, 'Guía de práctica: Práctica de impresión FDM')
        self.assertEqual(guia.codigo_guia, 'GP-FDM-01')
        self.assertEqual(guia.contenido['reserva_fuente_id'], reserva.pk)
        self.assertEqual(guia.contenido['duracion'], '2 h 30 min')
        self.assertEqual(guia.contenido['maximo_estudiantes'], 18)
        self.assertIn('FAB-UNIT-FDM-01', guia.contenido['equipos'][0])
        self.assertEqual(guia.contenido['software'], ['Ultimaker Cura'])
        self.assertEqual(guia.contenido['materiales'], '')
        self.assertEqual(guia.contenido['reactivos'], '')
        self.assertNotEqual(
            guia.contenido['manejo_residuos'],
            self.datos_completos()['manejo_residuos'],
        )
        self.assertIn('orden, limpieza', guia.contenido['manejo_residuos'])
        self.assertNotIn('Software:', '\n'.join(guia.contenido['equipos']))

        editor = self.client.get(
            reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk])
        )
        self.assertEqual(editor.status_code, 200)
        self.assertContains(editor, f'Datos operativos de {reserva.codigo_reserva}')
        self.assertContains(editor, 'Para cambiarlos solicita una modificación de la reserva')
        self.assertNotContains(editor, 'id_equipos')
        self.assertNotContains(editor, 'id_software')
        # Exacto: los materiales complementarios (id_materiales_complementarios)
        # si se editan; los insumos operativos no.
        self.assertNotContains(editor, 'id="id_materiales"')
        self.assertContains(editor, 'id="id_materiales_complementarios"')
        self.assertNotContains(editor, 'id_reactivos')
        self.assertNotContains(editor, 'id_manejo_residuos')

    def test_asignatura_y_precauciones_siguen_siendo_del_autor(self):
        """La reserva propone la asignatura, pero el docente escribe la oficial.

        Las precauciones propias de la actividad tampoco pueden perderse: la
        politica de la unidad las encabeza y no las reemplaza. Reeditar la guia
        no debe duplicar esas lineas institucionales.
        """
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Practica con nombre corto',
            unidad=self.unidad,
            responsable='Docente responsable',
            creado_por=self.autor,
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            actividad_catalogo=actividad,
            usuario=self.autor,
            fecha=date(2026, 9, 22),
            hora_inicio=time(8),
            hora_fin=time(10),
            equipo_codigo='EQ-DOC',
            equipo_nombre='Equipo docente',
            proposito_codigo='docencia_practica',
            provision_consumibles='ninguno',
            vinculacion_actividad='catalogo',
            referencia_actividad='Practica con nombre corto',
            responsable_actividad='Docente responsable',
            numero_participantes=12,
        )
        self.assertTrue(reserva.codigo_reserva, 'la senal debe poblar la instancia en memoria')

        self.client.force_login(self.autor)
        respuesta = self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]),
            self.datos_completos(
                actividad_existente=str(actividad.pk),
                reserva_referencia=str(reserva.pk),
                asignatura='Diseno y fabricacion digital',
                medidas_seguridad='Mantener despejada la zona de corte.',
                accion='guardar',
            ),
        )
        self.assertEqual(respuesta.status_code, 302, respuesta.content)

        guia = GuiaActividadReserva.objects.get(actividad=actividad, es_estructurada=True)
        self.assertEqual(guia.contenido['asignatura'], 'Diseno y fabricacion digital')
        # El apartado se almacena como texto con una linea por medida.
        seguridad = self.lineas(guia.contenido['medidas_seguridad'])
        self.assertIn('Mantener despejada la zona de corte.', seguridad)
        institucionales = [
            linea for linea in seguridad
            if linea != 'Mantener despejada la zona de corte.'
        ]
        self.assertTrue(institucionales, 'debe conservarse la politica de la unidad')
        self.assertEqual(seguridad[-1], 'Mantener despejada la zona de corte.')

        # El editor vuelve a mostrar unicamente lo que escribio el autor.
        editor = self.client.get(
            reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk])
        )
        self.assertEqual(editor.status_code, 200)
        self.assertContains(editor, 'Mantener despejada la zona de corte.')

        # Reeditar sin tocar el apartado no puede duplicar la politica.
        self.client.post(
            reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk]),
            self.datos_completos(
                actividad_existente=str(actividad.pk),
                reserva_referencia=str(reserva.pk),
                asignatura='Diseno y fabricacion digital',
                medidas_seguridad='Mantener despejada la zona de corte.',
                accion='guardar',
            ),
        )
        guia.refresh_from_db()
        seguridad_final = self.lineas(guia.contenido['medidas_seguridad'])
        self.assertEqual(seguridad_final, seguridad, 'la politica no debe duplicarse')

    def test_reserva_impide_sobrescribir_datos_operativos_desde_la_guia(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Práctica controlada',
            unidad=self.unidad,
            responsable='Docente responsable',
            creado_por=self.autor,
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            actividad_catalogo=actividad,
            usuario=self.autor,
            fecha=date(2026, 9, 16),
            hora_inicio=time(9),
            hora_fin=time(11),
            equipo_codigo='EQ-CONTROL',
            equipo_nombre='Equipo controlado',
            unidades_seleccionadas=json.dumps([
                {'codigo': 'EQ-CONTROL', 'nombre': 'Equipo controlado'}
            ]),
            proposito_codigo='docencia_practica',
            provision_consumibles='ninguno',
            vinculacion_actividad='catalogo',
            referencia_actividad='Asignatura controlada',
            responsable_actividad='Docente responsable',
            numero_participantes=10,
        )
        self.client.force_login(self.autor)
        response = self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]),
            self.datos_completos(
                actividad_existente=str(actividad.pk),
                reserva_referencia=str(reserva.pk),
                equipos='Equipo inventado',
                software='Licencia inventada',
                materiales='Material inventado',
                reactivos='Reactivo inventado',
                manejo_residuos='El usuario decide cómo desechar.',
                accion='guardar',
            ),
        )
        self.assertEqual(response.status_code, 302, response.content)
        guia = GuiaActividadReserva.objects.get(actividad=actividad, es_estructurada=True)
        self.assertIn('EQ-CONTROL', guia.contenido['equipos'][0])
        self.assertEqual(guia.contenido['software'], '')
        self.assertEqual(guia.contenido['materiales'], '')
        self.assertEqual(guia.contenido['reactivos'], '')
        self.assertNotIn('usuario decide', guia.contenido['manejo_residuos'].lower())
        self.assertIn('orden, limpieza', guia.contenido['manejo_residuos'])

    def test_apartados_complementarios_pueden_quedar_vacios(self):
        self.client.force_login(self.autor)
        data = self.datos_completos(
            fundamento_teorico='',
            medidas_seguridad='',
            resultados_esperados='',
            criterios_evaluacion='',
            manejo_residuos='',
            bibliografia='',
            equipos='',
            materiales='',
            reactivos='',
        )

        response = self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]), data,
        )

        self.assertEqual(response.status_code, 302, response.content)
        guia = GuiaActividadReserva.objects.get()
        self.assertEqual(guia.estado_publicacion, 'revision')
        self.assertEqual(guia.secciones_faltantes(), [])

    def test_vista_adapta_software_guardado_por_versiones_anteriores(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Práctica heredada',
            unidad=self.unidad,
            creado_por=self.autor,
            estado_publicacion='borrador',
            visibilidad='privada',
        )
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo='Guía heredada',
            es_estructurada=True,
            contenido={
                'laboratorio': self.unidad.nombre,
                'equipos': ['Impresora 3D', 'Software: Ultimaker Cura'],
            },
            estado_publicacion='borrador',
            subido_por=self.autor,
        )
        self.client.force_login(self.autor)

        response = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['contenido']['equipos'], ['Impresora 3D'])
        self.assertEqual(response.context['contenido']['software'], ['Ultimaker Cura'])

        # El expediente la lee incrustada: fragmento sin portal y encuadre propio.
        fragmento = self.client.get(
            reverse('ver_guia_actividad', args=[guia.pk]), {'fragmento': '1'}
        )
        self.assertEqual(fragmento.status_code, 200)
        self.assertContains(fragmento, 'guide-embed')
        self.assertContains(fragmento, 'guide-document')
        self.assertNotContains(fragmento, '<html')
        self.assertEqual(fragmento['X-Frame-Options'], 'SAMEORIGIN')

    def test_no_envia_una_guia_incompleta_a_revision(self):
        self.client.force_login(self.autor)
        data = self.datos_completos()
        data['procedimiento'] = ''
        response = self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]), data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Procedimiento')
        self.assertEqual(GuiaActividadReserva.objects.get().estado_publicacion, 'borrador')

    def test_flujo_revision_aprobacion_html_y_pdf(self):
        self.client.force_login(self.autor)
        response = self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]),
            self.datos_completos(),
        )
        guia = GuiaActividadReserva.objects.get()
        self.assertEqual(guia.estado_publicacion, 'revision')
        self.assertRedirects(response, f"{reverse('ver_guia_actividad', args=[guia.pk])}?guardado=1")
        plan = PlanificacionPractica.objects.create(
            actividad=guia.actividad,
            guia=None,
            requiere_guia=True,
            unidad=self.unidad,
            fecha=date(2026, 9, 15),
            hora_inicio=time(9, 0),
            hora_fin=time(11, 0),
            asignatura='Diseño asistido por computador',
            docente_tutor='Ing. Docente Responsable',
            tema='Práctica de manufactura digital',
            resultado_aprendizaje='Modelo terminado y validado',
            estudiantes_planificados=12,
            estado='borrador',
            creado_por=self.autor,
        )

        self.client.force_login(self.ajeno)
        self.assertEqual(
            self.client.get(reverse('ver_guia_actividad', args=[guia.pk])).status_code, 404
        )

        self.client.force_login(self.revisor)
        response = self.client.post(
            reverse('cambiar_estado_guia_practica', args=[guia.pk]),
            {'accion': 'aprobar', 'observacion': 'Contenido verificado.'},
        )
        self.assertEqual(response.status_code, 302)
        guia.refresh_from_db()
        self.assertEqual(guia.estado_publicacion, 'publicada')
        self.assertTrue(guia.es_vigente)
        self.assertEqual(guia.aprobado_por, self.revisor)
        self.assertEqual(guia.actividad.estado_publicacion, 'publicado')
        plan.refresh_from_db()
        self.assertEqual(plan.guia, guia)
        self.assertEqual(plan.estado, 'revision')

        html = self.client.get(reverse('ver_guia_actividad', args=[guia.pk]))
        self.assertEqual(html.status_code, 200)
        self.assertContains(html, 'Resultado(s) de aprendizaje vinculado(s)')
        self.assertContains(html, 'UPEC-P10-S01-FT04')
        self.assertContains(html, 'Modelo terminado y validado')
        self.assertContains(html, '<li>Construir un modelo bidimensional verificable.</li>', html=True)

        vista_pdf = self.client.get(
            reverse('ver_guia_actividad', args=[guia.pk]) + '?preview=pdf'
        )
        self.assertEqual(vista_pdf.status_code, 200)
        self.assertEqual(vista_pdf['Content-Type'], 'application/pdf')
        self.assertTrue(vista_pdf['Content-Disposition'].startswith('inline;'))
        self.assertTrue(vista_pdf.content.startswith(b'%PDF'))

        pdf = self.client.get(
            reverse('ver_guia_actividad', args=[guia.pk]) + '?download=1'
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertGreater(len(pdf.content), 3000)

    def test_revisor_devuelve_guia_con_observacion(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Actividad para devolver',
            unidad=self.unidad,
            creado_por=self.autor,
            estado_publicacion='revision',
            visibilidad='privada',
        )
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo='Guía para corrección',
            es_estructurada=True,
            contenido={'laboratorio': self.unidad.nombre},
            estado_publicacion='revision',
            subido_por=self.autor,
        )
        self.client.force_login(self.revisor)
        self.client.post(
            reverse('cambiar_estado_guia_practica', args=[guia.pk]),
            {'accion': 'rechazar', 'observacion': 'Completa la seguridad y el procedimiento.'},
        )
        guia.refresh_from_db()
        self.assertEqual(guia.estado_publicacion, 'rechazada')
        self.assertIn('Completa la seguridad', guia.observaciones_revision)

    def test_panel_muestra_guias_pendientes_de_la_unidad(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica', subtipo_actividad='practica_curricular',
            nombre='Actividad visible en el panel', unidad=self.unidad,
            creado_por=self.autor, estado_publicacion='revision', visibilidad='privada',
        )
        GuiaActividadReserva.objects.create(
            actividad=actividad, titulo='Guía pendiente visible', es_estructurada=True,
            estado_publicacion='revision', subido_por=self.autor,
        )
        self.client.force_login(self.revisor)
        response = self.client.get(
            reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=practicas'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Guía pendiente visible')
        self.assertEqual(response.context['guias_revision_total'], 1)

    def test_guia_conserva_version_publicada_y_audita_el_ciclo_documental(self):
        self.client.force_login(self.autor)
        self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]),
            self.datos_completos(),
        )
        publicada = GuiaActividadReserva.objects.get()

        self.client.force_login(self.revisor)
        self.client.post(
            reverse('cambiar_estado_guia_practica', args=[publicada.pk]),
            {'accion': 'aprobar', 'observacion': 'Versión inicial validada.'},
        )
        self.client.get(
            reverse('ver_guia_actividad', args=[publicada.pk]) + '?download=1'
        )
        response = self.client.post(
            reverse('cambiar_estado_guia_practica', args=[publicada.pk]),
            {'accion': 'nueva_version'},
        )

        nueva = GuiaActividadReserva.objects.exclude(pk=publicada.pk).get()
        self.assertRedirects(
            response,
            reverse(
                'editar_guia_practica',
                args=[self.unidad.slug, nueva.pk],
            ),
        )
        publicada.refresh_from_db()
        self.assertTrue(publicada.es_vigente)
        self.assertEqual(publicada.estado_publicacion, 'publicada')
        self.assertEqual(nueva.numero_version, publicada.numero_version + 1)
        self.assertEqual(nueva.estado_publicacion, 'borrador')
        self.assertFalse(nueva.es_vigente)
        contenido_publicado = dict(publicada.contenido)
        contenido_publicado.pop('firma_elaborador', None)
        self.assertEqual(nueva.contenido, contenido_publicado)
        self.assertNotIn('firma_elaborador', nueva.contenido)

        # Mientras exista una version en trabajo, no se abre otra: la vista
        # oculta el boton y el servidor redirige al borrador existente.
        vista = self.client.get(reverse('ver_guia_actividad', args=[publicada.pk]))
        self.assertNotContains(vista, 'value="nueva_version"')
        self.assertContains(vista, f'Continuar la versión {nueva.numero_version} en trabajo')
        repetida = self.client.post(
            reverse('cambiar_estado_guia_practica', args=[publicada.pk]),
            {'accion': 'nueva_version'},
        )
        self.assertRedirects(
            repetida,
            reverse('editar_guia_practica', args=[self.unidad.slug, nueva.pk]),
        )
        self.assertEqual(
            GuiaActividadReserva.objects.filter(estado_publicacion='borrador').count(), 1
        )

        self.client.post(
            reverse('cambiar_estado_guia_practica', args=[nueva.pk]),
            {'accion': 'archivar', 'observacion': 'Versión descartada.'},
        )
        nueva.refresh_from_db()
        self.assertFalse(nueva.activo)
        self.assertEqual(nueva.estado_publicacion, 'archivada')
        acciones = set(
            RegistroAuditoriaUnidad.objects.filter(
                unidad=self.unidad,
                entidad=GuiaActividadReserva._meta.label,
            ).values_list('accion', flat=True)
        )
        self.assertTrue({'enviar', 'aprobar', 'descargar', 'crear', 'archivar'} <= acciones)

    def test_lista_muestra_solo_version_vigente_y_ultima_en_trabajo(self):
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Actividad con historial documental',
            unidad=self.unidad,
            creado_por=self.autor,
            estado_publicacion='publicado',
            visibilidad='unidad',
        )
        anterior = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo='Versión histórica que no debe saturar la lista',
            numero_version=1,
            es_estructurada=True,
            estado_publicacion='publicada',
            activo=True,
            subido_por=self.autor,
        )
        vigente = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo='Versión publicada vigente',
            numero_version=2,
            es_estructurada=True,
            es_vigente=True,
            estado_publicacion='publicada',
            activo=True,
            subido_por=self.autor,
        )
        trabajo = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo='Nueva versión en trabajo',
            numero_version=3,
            es_estructurada=True,
            estado_publicacion='borrador',
            activo=True,
            subido_por=self.autor,
        )
        self.client.force_login(self.revisor)

        actual = self.client.get(reverse('lista_guias_practica', args=[self.unidad.slug]))
        historial = self.client.get(
            reverse('lista_guias_practica', args=[self.unidad.slug]) + '?historial=1'
        )

        # La lista entrega fichas: cada guía con la solicitud de la que viene.
        self.assertEqual([ficha['guia'] for ficha in actual.context['fichas']], [trabajo, vigente])
        self.assertNotContains(actual, anterior.titulo)
        self.assertContains(actual, 'Ver historial de versiones')
        self.assertEqual(
            [ficha['guia'] for ficha in historial.context['fichas']],
            [trabajo, vigente, anterior],
        )

        # La ficha señala de qué solicitud viene cada guía; sin reserva queda vacía.
        ficha = actual.context['fichas'][0]
        self.assertIn('reserva', ficha)
        self.assertIn('reserva_url', ficha)
        self.assertContains(actual, 'Sin solicitud asociada')
        self.assertContains(historial, anterior.titulo)

    def test_guia_en_revision_se_corrige_hasta_que_se_valide(self):
        """Enviada no es definitiva: se corrige mientras no se apruebe.

        Quien la escribio y el personal de la unidad pueden ajustarla, la huella
        de elaboracion se rehace con el contenido corregido y la version firmada
        con certificado cierra la edicion.
        """
        self.client.force_login(self.autor)
        self.client.post(
            reverse('nueva_guia_practica', args=[self.unidad.slug]),
            self.datos_completos(),
        )
        guia = GuiaActividadReserva.objects.get()
        self.assertEqual(guia.estado_publicacion, 'revision')
        self.assertTrue(guia.es_editable)

        respuesta = self.client.post(
            reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk]),
            self.datos_completos(
                actividad_existente=str(guia.actividad_id),
                accion='guardar',
                asignatura='Diseño asistido por computador II',
            ),
        )
        self.assertEqual(respuesta.status_code, 302, respuesta.content)
        guia.refresh_from_db()
        self.assertEqual(guia.estado_publicacion, 'revision')
        self.assertEqual(guia.contenido['asignatura'], 'Diseño asistido por computador II')
        self.assertTrue(
            verificar_firma_elaborador(guia),
            'la huella debe corresponder con el contenido corregido',
        )

        # El laboratorio abre el mismo editor sobre la version enviada.
        self.client.force_login(self.revisor)
        editor = self.client.get(
            reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk])
        )
        self.assertEqual(editor.status_code, 200)

        # Con la version firmada cargada ya no se puede reescribir el contenido.
        guia.archivo_firmado.save(
            'guia-firmada.pdf',
            SimpleUploadedFile('guia-firmada.pdf', b'%PDF-1.7 firmada', 'application/pdf'),
            save=True,
        )
        guia.refresh_from_db()
        self.assertFalse(guia.es_editable)
        cerrado = self.client.get(
            reverse('editar_guia_practica', args=[self.unidad.slug, guia.pk])
        )
        self.assertEqual(cerrado.status_code, 404)
        guia.archivo_firmado.delete(save=True)

    def test_lista_lleva_a_la_guia_publicada_o_a_la_reserva_pendiente(self):
        """La lista es el indice: cada guia abre donde se usa, sin repetir visor."""
        publicada_actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Práctica ya publicada',
            unidad=self.unidad,
            creado_por=self.autor,
            estado_publicacion='publicado',
            visibilidad='unidad',
        )
        publicada = GuiaActividadReserva.objects.create(
            actividad=publicada_actividad,
            titulo='Guía publicada para la comunidad',
            numero_version=1,
            es_estructurada=True,
            es_vigente=True,
            estado_publicacion='publicada',
            visibilidad='unidad',
            activo=True,
            subido_por=self.autor,
        )
        pendiente_actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Práctica pendiente de firma',
            unidad=self.unidad,
            creado_por=self.autor,
        )
        reserva = Reserva.objects.create(
            laboratorio=self.unidad,
            actividad_catalogo=pendiente_actividad,
            usuario=self.autor,
            fecha=date(2026, 10, 6),
            hora_inicio=time(8),
            hora_fin=time(10),
            equipo_codigo='EQ-PEND',
            equipo_nombre='Equipo de la práctica pendiente',
            proposito_codigo='docencia_practica',
            provision_consumibles='ninguno',
            vinculacion_actividad='catalogo',
            referencia_actividad='Práctica pendiente de firma',
            responsable_actividad='Docente responsable',
            numero_participantes=10,
        )
        pendiente = GuiaActividadReserva.objects.create(
            actividad=pendiente_actividad,
            titulo='Guía enviada a revisión',
            numero_version=1,
            es_estructurada=True,
            estado_publicacion='revision',
            activo=True,
            subido_por=self.autor,
        )
        self.client.force_login(self.autor)

        respuesta = self.client.get(reverse('lista_guias_practica', args=[self.unidad.slug]))

        destinos = {
            ficha['guia'].pk: ficha['destino']
            for ficha in respuesta.context['fichas']
        }
        self.assertEqual(
            destinos[publicada.pk]['url'],
            f'{self.unidad.get_absolute_url()}?guia={publicada.pk}#docencia-capacitacion',
        )
        self.assertEqual(
            destinos[pendiente.pk]['url'],
            f'{self.unidad.get_absolute_url()}?reserva={reserva.pk}#mis-reservas',
        )
        self.assertContains(respuesta, 'Ver en Docencia y capacitación')
        self.assertContains(respuesta, 'Firmar o corregir en mis reservas')
        # El visor ya no se repite en esta pantalla.
        self.assertNotContains(respuesta, 'Ver documento')

    def test_permiso_de_reservas_no_concede_revision_de_guias(self):
        User = get_user_model()
        operador_reservas = User.objects.create_user(
            'operador-solo-reservas', password='clave-segura'
        )
        ResponsableUnidad.objects.create(
            unidad=self.unidad,
            usuario=operador_reservas,
            rol='soporte',
            recibe_reservas=True,
            activo=True,
            permisos_operativos={
                'reservas': True,
                'agenda': False,
                'recursos': False,
                'mantenimiento': False,
                'inventario': False,
                'practicas': False,
                'reportes': False,
                'configuracion': False,
                'corregir_cerradas': False,
            },
        )
        actividad = CatalogoActividadReserva.objects.create(
            proposito_codigo='docencia_practica',
            subtipo_actividad='practica_curricular',
            nombre='Actividad documental restringida',
            unidad=self.unidad,
            creado_por=self.autor,
            estado_publicacion='revision',
            visibilidad='privada',
        )
        guia = GuiaActividadReserva.objects.create(
            actividad=actividad,
            titulo='Guía restringida',
            es_estructurada=True,
            contenido={'laboratorio': self.unidad.nombre},
            estado_publicacion='revision',
            subido_por=self.autor,
        )
        self.client.force_login(operador_reservas)

        response = self.client.post(
            reverse('cambiar_estado_guia_practica', args=[guia.pk]),
            {'accion': 'aprobar'},
        )

        self.assertEqual(response.status_code, 404)
        guia.refresh_from_db()
        self.assertEqual(guia.estado_publicacion, 'revision')
