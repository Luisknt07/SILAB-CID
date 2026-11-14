"""El aula calificable: un escenario por estudiante, corregido por el motor.

Sobre la Planta Piloto de Lácteos cargada: el docente arma un ejercicio sobre
un proceso y uno de los tres simuladores, la plataforma reparte una escala
distinta a cada participante de la sesión, el estudiante responde con el
simulador abierto y la corrección compara con el mismo motor que la planta usa
para producir.
"""

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.formacion.presentation.ejercicios import preguntas_de, url_del_simulador
from apps.formacion.models.aula import EjercicioAula, IntentoEjercicio
from apps.reservas.models.reservas import Reserva
from tests.integration.test_laboratorios_institucionales import identificar
from tests.integration.test_reserva_por_proceso import BasePracticaPorProceso


class BaseEjercicios(BasePracticaPorProceso):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Usuario = get_user_model()
        cls.estudiante_dos = Usuario.objects.create_user(
            username='estudiante.dos.lacteos',
            password='Prueba-Lacteos-2026',
            email='estudiante.dos.lacteos@upec.edu.ec',
            first_name='Ana',
            last_name='Benalcázar',
        )
        identificar(cls.estudiante_dos, tipo_usuario='estudiante')

    def sesion_con_estudiantes(self):
        """Una práctica por proceso con dos estudiantes inscritos."""
        seleccion = self.seleccion('2')
        datos = self.carga_docencia(
            seleccion,
            participantes_seleccionados=json.dumps([self.estudiante.pk, self.estudiante_dos.pk]),
        )
        respuesta = self.reservar(datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        reserva = Reserva.objects.get(pk=respuesta.json()['reserva_id'])
        self.assertEqual(reserva.participantes.count(), 2)
        return reserva

    def crear_ejercicio(self, reserva=None, **extra):
        datos = {
            'modulo': 'ejercicio_aula',
            'nombre': 'Balance de energía del queso fresco',
            'simulador': 'balance',
            'receta_id': self.receta_queso.pk,
            'consigna': 'Abre el simulador con tu escala y responde los cuatro valores del balance.',
            'factor_base': '1',
            'paso': '0.5',
            'tolerancia_pct': '2',
            'puntaje': '10',
            'estado': 'abierto',
        }
        if reserva is not None:
            datos['reserva_id'] = reserva.pk
        datos.update(extra)
        respuesta = self.operar(**datos)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return EjercicioAula.objects.get(pk=respuesta.json()['registro']['id'])

    def asignar(self, ejercicio):
        return self.operar(
            modulo='ejercicio_aula',
            registro_id=ejercicio.pk,
            accion_ejercicio='asignar',
        )

    def ejercicio_asignado(self, **extra):
        reserva = self.sesion_con_estudiantes()
        ejercicio = self.crear_ejercicio(reserva, **extra)
        self.assertEqual(self.asignar(ejercicio).status_code, 200)
        return ejercicio

    def intento_de(self, ejercicio, estudiante):
        return IntentoEjercicio.objects.get(ejercicio=ejercicio, estudiante=estudiante)

    def esperado_de(self, intento, clave):
        """Lo que el motor calcula para esa pregunta a la escala que le tocó al estudiante."""
        return next(
            pregunta for pregunta in preguntas_de(intento.ejercicio, intento.factor)
            if pregunta['clave'] == clave
        )

    def responder(self, intento, **cambios):
        """Entrega las respuestas correctas del motor, con lo que la prueba quiera cambiar."""
        datos = {
            pregunta['clave']: pregunta['esperado_texto']
            for pregunta in preguntas_de(intento.ejercicio, intento.factor)
        }
        datos.update(cambios)
        self.client.force_login(intento.estudiante)
        return self.client.post(
            reverse('resolver_ejercicio', args=[self.unidad.slug, intento.pk]), datos,
        )


class LaAsignacionTests(BaseEjercicios):
    def test_cada_estudiante_recibe_su_propia_escala(self):
        ejercicio = self.ejercicio_asignado()
        intentos = list(ejercicio.intentos.select_related('estudiante').order_by('factor'))
        # Los dos participantes y quien pidió la sesión.
        self.assertEqual(len(intentos), 3)
        self.assertEqual([intento.factor for intento in intentos], [
            Decimal('1.000'), Decimal('1.500'), Decimal('2.000'),
        ])
        self.assertEqual({intento.estado for intento in intentos}, {'asignado'})
        self.assertTrue(ejercicio.codigo.startswith('EJ'))
        ejercicio.refresh_from_db()
        self.assertEqual(ejercicio.estado, 'abierto')
        # Volver a asignar no cambia la escala de quien ya la tenía.
        respuesta = self.asignar(ejercicio)
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertIn('0 estudiantes nuevos', respuesta.json()['message'])
        self.assertEqual(ejercicio.intentos.count(), 3)

    def test_un_ejercicio_sin_sesion_no_se_asigna(self):
        ejercicio = self.crear_ejercicio(None, estado='borrador')
        respuesta = self.asignar(ejercicio)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('necesita una sesión', respuesta.json()['error'])

    def test_el_paso_en_cero_da_a_todos_la_misma_escala(self):
        ejercicio = self.ejercicio_asignado(paso='0', factor_base='3')
        self.assertEqual(
            {intento.factor for intento in ejercicio.intentos.all()}, {Decimal('3.000')},
        )


class LasPreguntasTests(BaseEjercicios):
    def test_el_balance_pregunta_lo_que_el_motor_calcula_a_esa_escala(self):
        ejercicio = self.crear_ejercicio(None)
        preguntas = {pregunta['clave']: pregunta for pregunta in preguntas_de(ejercicio, Decimal('2'))}
        self.assertEqual(set(preguntas), {'masa_entrada', 'producto', 'calor_kwh', 'vapor_kg'})
        # Doscientos litros de leche a 1,03 kg por litro pesan 206 kg.
        self.assertEqual(preguntas['masa_entrada']['esperado'], Decimal('206.00'))
        # Dos corridas base rinden 24 kg de queso fresco.
        self.assertEqual(preguntas['producto']['esperado'], Decimal('24.00'))
        self.assertGreater(preguntas['calor_kwh']['esperado'], Decimal('0'))
        self.assertEqual(preguntas['producto']['unidad'], 'kg')
        # A otra escala, otros números: nadie copia al compañero.
        otras = {pregunta['clave']: pregunta for pregunta in preguntas_de(ejercicio, Decimal('3'))}
        self.assertEqual(otras['masa_entrada']['esperado'], Decimal('309.00'))
        self.assertEqual(otras['producto']['esperado'], Decimal('36.00'))

    def test_la_linea_pregunta_el_takt_el_cuello_y_las_estaciones(self):
        ejercicio = self.crear_ejercicio(None, simulador='linea', jornada='8')
        preguntas = {pregunta['clave']: pregunta for pregunta in preguntas_de(ejercicio, Decimal('2'))}
        self.assertEqual(set(preguntas), {'takt', 'ciclo', 'estaciones', 'eficiencia'})
        # Dos corridas en una jornada de ocho horas: 240 minutos de takt.
        self.assertEqual(preguntas['takt']['esperado'], Decimal('240.00'))
        self.assertGreater(preguntas['estaciones']['esperado'], Decimal('0'))

    def test_los_materiales_preguntan_la_materia_prima_y_lo_que_falta(self):
        ejercicio = self.crear_ejercicio(None, simulador='materiales')
        preguntas = {pregunta['clave']: pregunta for pregunta in preguntas_de(ejercicio, Decimal('2'))}
        self.assertEqual(set(preguntas), {'materia_prima', 'insumos', 'faltantes', 'producto'})
        # Dos corridas base piden doscientos litros de leche cruda.
        self.assertEqual(preguntas['materia_prima']['esperado'], Decimal('200.00'))
        self.assertEqual(preguntas['insumos']['esperado'], Decimal('7.00'))
        self.assertIn('Leche cruda', preguntas['materia_prima']['texto'])

    def test_el_enlace_abre_el_simulador_con_los_datos_del_estudiante(self):
        ejercicio = self.crear_ejercicio(None)
        url = url_del_simulador(ejercicio, Decimal('1.5'))
        self.assertIn(reverse('simulador_balance', args=[self.unidad.slug]), url)
        self.assertIn(f'receta={self.receta_queso.pk}', url)
        self.assertIn('cantidad=150', url)
        linea = self.crear_ejercicio(None, simulador='linea', jornada='6')
        self.assertIn('corridas=1.5', url_del_simulador(linea, Decimal('1.5')))
        self.assertIn('jornada=6', url_del_simulador(linea, Decimal('1.5')))


class LaEntregaTests(BaseEjercicios):
    def test_la_respuesta_correcta_se_lleva_todo_el_puntaje(self):
        ejercicio = self.ejercicio_asignado()
        intento = self.intento_de(ejercicio, self.estudiante)
        respuesta = self.responder(intento)
        self.assertEqual(respuesta.status_code, 302, getattr(respuesta, 'content', b'')[:300])
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'calificado')
        self.assertEqual(intento.puntaje, Decimal('10.00'))
        self.assertEqual(intento.aciertos, 4)
        self.assertIsNotNone(intento.entregado_en)
        self.assertTrue(all(fila['correcta'] for fila in intento.resultados))

    def test_una_respuesta_fuera_de_tolerancia_pierde_solo_su_pregunta(self):
        ejercicio = self.ejercicio_asignado()
        intento = self.intento_de(ejercicio, self.estudiante)
        esperado = self.esperado_de(intento, 'masa_entrada')
        self.assertEqual(self.responder(intento, masa_entrada='1').status_code, 302)
        intento.refresh_from_db()
        self.assertEqual(intento.aciertos, 3)
        self.assertEqual(intento.puntaje, Decimal('7.50'))
        fallada = next(fila for fila in intento.resultados if fila['clave'] == 'masa_entrada')
        self.assertFalse(fallada['correcta'])
        self.assertEqual(fallada['respuesta'], '1')
        self.assertEqual(fallada['esperado'], esperado['esperado_texto'])

    def test_una_diferencia_dentro_de_la_tolerancia_se_acepta(self):
        ejercicio = self.ejercicio_asignado(tolerancia_pct='5')
        intento = self.intento_de(ejercicio, self.estudiante)
        # Un tres por ciento por debajo del valor del motor entra en la tolerancia del cinco.
        aproximada = (self.esperado_de(intento, 'masa_entrada')['esperado'] * Decimal('0.97')).quantize(
            Decimal('0.01')
        )
        self.assertEqual(self.responder(intento, masa_entrada=str(aproximada)).status_code, 302)
        intento.refresh_from_db()
        self.assertEqual(intento.aciertos, 4)

    def test_el_estudiante_no_ve_el_valor_esperado_antes_de_entregar(self):
        ejercicio = self.ejercicio_asignado()
        intento = self.intento_de(ejercicio, self.estudiante)
        self.client.force_login(self.estudiante)
        pagina = self.client.get(reverse('resolver_ejercicio', args=[self.unidad.slug, intento.pk]))
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Entregar el ejercicio')
        esperado = self.esperado_de(intento, 'masa_entrada')['esperado_texto']
        self.assertNotContains(pagina, esperado)
        self.assertEqual(
            {pregunta['esperado_texto'] for pregunta in pagina.context['preguntas']}, {''},
        )
        # Después de entregar, la página dice qué calculaba el motor.
        self.assertEqual(self.responder(intento).status_code, 302)
        pagina = self.client.get(reverse('resolver_ejercicio', args=[self.unidad.slug, intento.pk]))
        self.assertContains(pagina, esperado)
        self.assertContains(pagina, '10 de 10')

    def test_nadie_entrega_el_ejercicio_de_otro(self):
        ejercicio = self.ejercicio_asignado()
        intento = self.intento_de(ejercicio, self.estudiante)
        self.client.force_login(self.estudiante_dos)
        pagina = self.client.get(reverse('resolver_ejercicio', args=[self.unidad.slug, intento.pk]))
        self.assertEqual(pagina.status_code, 403)
        respuesta = self.client.post(
            reverse('resolver_ejercicio', args=[self.unidad.slug, intento.pk]), {'masa_entrada': '206'},
        )
        self.assertEqual(respuesta.status_code, 403)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'asignado')

    def test_un_ejercicio_cerrado_ya_no_admite_entregas(self):
        ejercicio = self.ejercicio_asignado()
        respuesta = self.operar(
            modulo='ejercicio_aula', registro_id=ejercicio.pk, accion='desactivar',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        ejercicio.refresh_from_db()
        self.assertEqual(ejercicio.estado, 'cerrado')
        intento = self.intento_de(ejercicio, self.estudiante)
        pagina = self.responder(intento)
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'no está abierto')
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'asignado')

    def test_mis_ejercicios_lista_lo_asignado_con_su_escala(self):
        ejercicio = self.ejercicio_asignado()
        self.client.force_login(self.estudiante)
        pagina = self.client.get(reverse('mis_ejercicios', args=[self.unidad.slug]))
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual(pagina.headers['X-Frame-Options'], 'SAMEORIGIN')
        self.assertContains(pagina, ejercicio.nombre)
        self.assertContains(pagina, 'Resolver')
        self.assertEqual(len(pagina.context['filas']), 1)
        self.assertEqual(len(pagina.context['pendientes']), 1)


class ElPanelDelAulaTests(BaseEjercicios):
    def test_la_pestana_muestra_los_ejercicios_y_sus_entregas(self):
        ejercicio = self.ejercicio_asignado()
        intento = self.intento_de(ejercicio, self.estudiante)
        self.assertEqual(self.responder(intento).status_code, 302)
        self.client.force_login(self.coordinacion)
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'ejercicios'})
        self.assertEqual(panel.status_code, 200)
        secciones = {item['clave']: item['habilitada'] for item in panel.context['secciones_gestion']}
        self.assertTrue(secciones['ejercicios'])
        self.assertContains(panel, 'data-management-view="ejercicios"')
        self.assertContains(panel, 'data-agenda-operation-form="ejercicio_aula"')
        self.assertContains(panel, 'data-agenda-operation-form="asignar_ejercicio"')
        self.assertContains(panel, 'data-agenda-operation-form="intento_ejercicio"')
        self.assertContains(panel, ejercicio.codigo)
        self.assertContains(panel, 'Benalcázar')
        fila = next(item for item in panel.context['ejercicios_aula'] if item['ejercicio'] == ejercicio)
        self.assertEqual(fila['resumen']['asignados'], 3)
        self.assertEqual(fila['resumen']['entregados'], 1)
        self.assertEqual(fila['resumen']['promedio'], Decimal('10.00'))

    def test_el_docente_ajusta_la_nota_y_comenta(self):
        ejercicio = self.ejercicio_asignado()
        intento = self.intento_de(ejercicio, self.estudiante)
        self.assertEqual(self.responder(intento, masa_entrada='1').status_code, 302)
        respuesta = self.operar(
            modulo='intento_ejercicio',
            registro_id=intento.pk,
            puntaje='8.5',
            comentario='El procedimiento estaba bien; revisa la densidad de la leche.',
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        intento.refresh_from_db()
        self.assertEqual(intento.puntaje, Decimal('8.50'))
        self.assertIn('densidad', intento.comentario)

    def test_la_nota_no_puede_superar_la_del_ejercicio(self):
        ejercicio = self.ejercicio_asignado()
        intento = self.intento_de(ejercicio, self.estudiante)
        respuesta = self.operar(
            modulo='intento_ejercicio', registro_id=intento.pk, puntaje='20',
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('no puede superar', respuesta.json()['error'])

    def test_la_hoja_de_resultados_la_ve_quien_conduce_las_practicas(self):
        ejercicio = self.ejercicio_asignado()
        intento = self.intento_de(ejercicio, self.estudiante)
        self.assertEqual(self.responder(intento).status_code, 302)
        self.client.force_login(self.coordinacion)
        hoja = self.client.get(reverse('resultados_ejercicio', args=[self.unidad.slug, ejercicio.pk]))
        self.assertEqual(hoja.status_code, 200)
        self.assertContains(hoja, ejercicio.nombre)
        self.assertContains(hoja, 'ESTUDIANTES')
        self.assertContains(hoja, 'Benalcázar')
        self.client.force_login(self.estudiante)
        negada = self.client.get(reverse('resultados_ejercicio', args=[self.unidad.slug, ejercicio.pk]))
        self.assertEqual(negada.status_code, 403)

    def test_la_ficha_publica_ofrece_mis_ejercicios_en_los_simuladores(self):
        pagina = self.client.get(self.unidad.get_absolute_url())
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, 'Mis ejercicios')
        self.assertContains(pagina, reverse('mis_ejercicios', args=[self.unidad.slug]))
