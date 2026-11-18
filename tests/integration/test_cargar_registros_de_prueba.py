"""El comando que carga, por las pantallas, un registro de prueba en cada documento del Centro de reportes.

Se prueba sobre una unidad que imita al FabLab: su cuenta que administra y coordina, otra persona del equipo humano
con cuenta que valida, un estudiante que reserva y valora, una persona del equipo sin cuenta y la Dirección con su
función de seguimiento. La carga se ensaya (no deja nada), se aplica (cada documento muestra su registro) y se
retira con su manifiesto (la base vuelve a como estaba, también lo que ya existía y se cambió).
"""
import json
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.roles import MODULOS_OPERATIVOS
from apps.directorio_unidades.models.core import Unidad
from apps.documentos.models.expediente import DocumentoExpediente
from apps.documentos.presentation.expediente import construir_expediente, cortes_del_anio, periodo_vigente
from apps.documentos.presentation.expediente_catalogo import asegurar_catalogo
from apps.gestion_unidades.models.espacios import EspacioReservable, ResponsableUnidad
from apps.integraciones.carga_de_prueba import ANEXOS, PRINCIPALES, RESPALDO
from apps.recursos.models.software import SoftwareDisponible
from apps.recursos.models.unidades import UnidadEquipo
from tests.integration.test_seguimiento_gobernanza import designar
from tests.integration.utiles import abrir_entrega, identificar


def _conteos():
    return {m._meta.label: m._base_manager.count() for m in apps.get_models()
            if not m._meta.proxy and m._meta.managed and m._meta.app_label != 'centros_id'
            and m._meta.label != 'sessions.Session'}


def _archivos(carpeta):
    return sorted(p.relative_to(carpeta).as_posix() for p in Path(carpeta).rglob('*') if p.is_file())


@override_settings(MEDICION_METAS_HABILITADA=True, MEDICION_SOLO_DEMO=False)
class CargarRegistrosDePruebaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        asegurar_catalogo()
        usuarios = get_user_model().objects
        cls.admin = usuarios.create_user('admin.lab-carga-j', first_name='Ada', last_name='Administradora')
        identificar(cls.admin, tipo_usuario='administrativo', carrera='')
        cls.coordinadora = usuarios.create_user('coordinacion.lab-carga-j', first_name='Coral', last_name='Coordinadora')
        identificar(cls.coordinadora, tipo_usuario='administrativo', carrera='')
        cls.estudiante = usuarios.create_user('estudiante.lab-carga-j', first_name='Eva', last_name='Estudiante')
        identificar(cls.estudiante, tipo_usuario='estudiante')
        cls.direccion = usuarios.create_superuser('direccion.lab-carga-j', 'direccion.lab-carga-j@example.org',
                                                  'clave-ficticia', first_name='Dina', last_name='Directora')
        designar(cls.direccion)
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio ficticio de la carga J', slug='laboratorio-carga-j', dependencia='laboratorios',
            descripcion='Unidad ficticia que imita al FabLab.', fecha_inicio=date(2025, 1, 1),
            administrador=cls.admin, activo=True)
        permisos = {modulo: True for modulo in MODULOS_OPERATIVOS}
        ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.admin, nombre='Ada Administradora',
                                         rol='coordinacion', permisos_operativos=permisos, activo=True,
                                         recibe_reservas=True)
        ResponsableUnidad.objects.create(unidad=cls.unidad, usuario=cls.coordinadora, nombre='Coral Coordinadora',
                                         rol='coordinacion', permisos_operativos=permisos, activo=True)
        cls.persona = ResponsableUnidad.objects.create(unidad=cls.unidad, nombre='Persona ficticia sin cuenta',
                                                       rol='laboratorista', formacion='Formación original ficticia',
                                                       email='persona.ficticia@example.org', activo=True)
        cls.sala = EspacioReservable.objects.create(unidad=cls.unidad, codigo='SALA-J', nombre='Sala ficticia J',
                                                    tipo='sala', capacidad=20, activo=True, reservable=True)
        SoftwareDisponible.objects.create(unidad=cls.unidad, nombre='Programa ficticio J', codigo='SW-J', activo=True)
        # Los plazos dependen del calendario: aquí se abren las entregas para hablar de la carga, no del plazo.
        hoy = timezone.localdate()
        cls.anio, cls.corte = hoy.year, periodo_vigente(cortes_del_anio(hoy.year), hoy)
        construir_expediente(cls.unidad, cls.anio)
        for documento in DocumentoExpediente.objects.filter(unidad=cls.unidad, anio=cls.anio).select_related('exigido'):
            if documento.exigido.codigo in ('PLAN-COMPRAS-ANUAL', 'PLANIFICACION'):
                abrir_entrega(documento)

    def setUp(self):
        medios = TemporaryDirectory(prefix='carga-j-', ignore_cleanup_errors=True)
        self.addCleanup(medios.cleanup)
        self.medios = medios.name
        ajuste = override_settings(MEDIA_ROOT=self.medios)
        ajuste.enable()
        self.addCleanup(ajuste.disable)
        manifiestos = TemporaryDirectory(prefix='manifiestos-j-', ignore_cleanup_errors=True)
        self.addCleanup(manifiestos.cleanup)
        self.carpeta = manifiestos.name

    def comando(self, *argumentos, **opciones):
        salida = StringIO()
        call_command('cargar_registros_de_prueba', *argumentos, unidad=self.unidad.slug,
                     cuenta_unidad=self.admin.username, usuario=self.estudiante.username,
                     direccion=self.direccion.username, carpeta=self.carpeta, stdout=salida, **opciones)
        return salida.getvalue()

    def test_aplicar_exige_el_nombre_de_la_base_conectada(self):
        with self.assertRaisesMessage(CommandError, f'Para aplicar indique --base {connection.settings_dict["NAME"]}'):
            self.comando(aplicar=True, base='otra-base')
        self.assertFalse(UnidadEquipo.objects.filter(laboratorio=self.unidad).exists())

    def test_ensaya_aplica_cada_documento_muestra_su_registro_y_se_retira_de_ida_y_vuelta(self):
        antes, persona = _conteos(), self.persona.formacion

        # Ensayo: recorre todo, informa y no deja ni filas ni archivos.
        salida = self.comando()
        self.assertIn('Ensayo terminado: no se cambió nada.', salida)
        self.assertIn(f'valida: {self.coordinadora.username}', salida)
        self.assertEqual(_conteos(), antes)
        self.assertEqual(_archivos(self.medios), [])

        # Aplicar: deja el manifiesto y un registro válido que aparece en cada documento.
        salida = self.comando(aplicar=True, base=connection.settings_dict['NAME'])
        self.assertIn('Carga aplicada.', salida)
        self.assertNotIn('filas nuevas ajenas a la carga', salida)
        [ruta] = list(Path(self.carpeta).glob('*.json'))
        self.assertEqual(ruta.name, f'{timezone.localdate():%Y-%m-%d}-{self.unidad.slug}.json')
        manifiesto = json.loads(ruta.read_text(encoding='utf-8'))
        registros = manifiesto['registros']
        self.assertEqual({r['documento'] for r in registros}, {c for c, _n in ANEXOS + RESPALDO + PRINCIPALES})
        for registro in registros:
            with self.subTest(documento=registro['documento'], tabla=registro['tabla']):
                if registro['documento'] == 'TRANSFERENCIA' and registro['estado'].startswith('NO CARGADO'):
                    # La unidad ficticia no publica servicios: el informe lo dice en lugar de inventar uno.
                    self.assertIn('no tiene servicios publicados', registro['estado'])
                    continue
                self.assertFalse(registro['estado'].startswith('NO CARGADO'), registro['estado'])
                self.assertIn(registro['aparece'], ('sí', 'n/a'), registro)
        estados = {r['documento']: r['estado'] for r in registros if r['tabla'] == 'Documento'}
        for codigo in ('RESOLUCION-CREACION', 'PROTOCOLO-BIOSEGURIDAD', 'REGLAMENTO-USO', 'PLAN-COMPRAS-ANUAL',
                       'PLANIFICACION'):
            self.assertEqual(estados[codigo], 'Enviado y aprobado por la Dirección', codigo)
        self.assertTrue(estados['INFORME-SEMESTRAL'].startswith('Borrador guardado'))
        # Lo que ya existía y cambió queda con su valor anterior en el manifiesto; los documentos, aparte.
        self.persona.refresh_from_db()
        self.assertTrue(self.persona.formacion.startswith('[PRUEBA] '))
        cambio = next(m for m in manifiesto['modificados'] if m['modelo'] == 'gestion_unidades.ResponsableUnidad'
                      and m['pk'] == self.persona.pk)
        self.assertEqual(cambio['antes']['formacion'], persona)
        self.assertTrue(manifiesto['documentos_del_expediente'])
        self.assertTrue(manifiesto['archivos'])
        self.assertTrue(all(nombre in _archivos(self.medios) for nombre in manifiesto['archivos']))
        # Los textos libres van marcados y los códigos elegidos empiezan con PRUEBA-.
        equipo = UnidadEquipo.objects.get(laboratorio=self.unidad, codigo_unidad='PRUEBA-EQ-01')
        self.assertTrue(equipo.equipo.nombre.startswith('[PRUEBA] '))
        # Una segunda carga sin retirar la primera se rechaza.
        with self.assertRaisesMessage(CommandError, 'ya tiene una carga de prueba'):
            self.comando()

        # Retirar: se ensaya primero y después se aplica; la base y MEDIA_ROOT vuelven a como estaban.
        salida = self.comando(retirar=str(ruta))
        self.assertIn('Ensayo del retiro terminado: no se cambió nada.', salida)
        self.assertTrue(UnidadEquipo.objects.filter(pk=equipo.pk).exists())
        salida = self.comando(retirar=str(ruta), aplicar=True, base=connection.settings_dict['NAME'])
        self.assertIn('Carga de prueba retirada.', salida)
        self.assertEqual(_conteos(), antes)
        self.assertEqual(_archivos(self.medios), [])
        self.persona.refresh_from_db()
        self.assertEqual(self.persona.formacion, persona)
        self.assertTrue(json.loads(ruta.read_text(encoding='utf-8'))['retirado_en'])
        with self.assertRaisesMessage(CommandError, 'Esa carga ya se retiró'):
            self.comando(retirar=str(ruta), aplicar=True, base=connection.settings_dict['NAME'])

    def test_lo_cambiado_despues_de_la_carga_no_se_toca_al_retirar(self):
        salida = self.comando(aplicar=True, base=connection.settings_dict['NAME'])
        self.assertIn('Carga aplicada.', salida)
        [ruta] = list(Path(self.carpeta).glob('*.json'))
        # Alguien corrige a mano la formación de la persona después de la carga.
        ResponsableUnidad.objects.filter(pk=self.persona.pk).update(formacion='Corregida por la unidad')
        salida = self.comando(retirar=str(ruta), aplicar=True, base=connection.settings_dict['NAME'])
        self.assertIn(f'gestion_unidades.ResponsableUnidad {self.persona.pk}: cambió después de la carga; no se toca',
                      salida)
        self.persona.refresh_from_db()
        self.assertEqual(self.persona.formacion, 'Corregida por la unidad')
        self.assertFalse(UnidadEquipo.objects.filter(laboratorio=self.unidad, codigo_unidad='PRUEBA-EQ-01').exists())
