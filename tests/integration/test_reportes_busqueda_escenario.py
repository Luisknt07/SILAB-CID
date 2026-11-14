"""Todas las métricas de asignaturas responden a la misma búsqueda."""
from datetime import time

from apps.formacion.presentation.asignaturas import reporte_asignaturas
from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.reservas.models.reservas import ProgramacionReserva, Reserva
from tests.integration.test_reportes_evidencias import BaseDeReportes


class EscenarioEnLaBusquedaTests(BaseDeReportes):
    def test_una_sesion_con_escenario_no_hereda_pendientes_de_sesiones_excluidas(self):
        programa = ProgramacionReserva.objects.create(laboratorio=self.unidad, solicitante=self.coordinador,
            fecha_inicio=self.desde, fecha_fin=self.hasta, dia_semana=0, hora_inicio=time(9), hora_fin=time(11))
        self.reserva(programacion=programa, codigo_reserva='QA-EXCLUIDA')
        seleccionada = self.reserva(programacion=programa, codigo_reserva='QA-SELECCIONADA')
        espacio = EspacioReservable.objects.create(unidad=self.unidad, codigo='QA-ESC', nombre='Sala QA')
        seleccionada.espacios_solicitados.add(espacio)
        _headers, filas, tarjetas, _estados = reporte_asignaturas(self.unidad, self.desde, self.hasta,
            search='QA-SELECCIONADA')
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0][1], 2)
        self.assertEqual(tarjetas[0][1], 1)
        self.assertEqual(tarjetas[-1][1], 0)
        self.assertEqual(Reserva.objects.filter(programacion=programa).count(), 2)
