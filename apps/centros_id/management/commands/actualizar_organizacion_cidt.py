"""Actualiza la precarga reconocida del CIDT sin sustituir ediciones manuales."""
import re
from django.core.management.base import BaseCommand, CommandError
from django.db import router, transaction

from apps.centros_id.contenido import cidt
from apps.centros_id.models import (
    Articulacion, CentroID, Componente, EquipoCentro, PasoProceso, ProcesoArea, Servicio,
)
from apps.centros_id.texto import pares_de


class Command(BaseCommand):
    help = 'Revisa organización CIDT; --aplicar actualiza sólo vacíos y valores de precarga reconocidos.'

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true')

    def handle(self, *args, **options):
        alias = router.db_for_write(CentroID)
        self.cambios = 0
        self.conflictos = []
        with transaction.atomic(using=alias):
            centro = CentroID.objects.select_for_update().filter(slug='cidt-upec').first()
            if centro is None:
                raise CommandError('Cargue primero el catálogo del CIDT; no se crea otro centro.')
            areas = {a.codigo: a for a in centro.componentes.select_for_update()}
            revision = cidt.REVISION_ORGANIZACION
            if set(revision['componentes']) - areas.keys():
                raise CommandError('Faltan áreas del catálogo; no se modifica una organización parcial.')
            self.actualizar(centro, revision['centro'])
            for codigo, datos in revision['componentes'].items():
                antes, despues = dict(datos['antes']), dict(datos['despues'])
                padre = despues.pop('integrado_en_codigo', '')
                antes.pop('integrado_en_codigo', None)
                if padre:
                    antes['integrado_en'] = None
                    despues['integrado_en'] = areas[padre]
                self.actualizar(areas[codigo], {'antes': antes, 'despues': despues})
                if 'proceso_anterior' in datos:
                    self.proceso(areas[codigo], datos)
            etiquetas_anteriores = {'División tecnológica': 'division',
                'Plataforma operativa de validación': 'plataforma', 'Plataforma transversal': 'transversal'}
            for anterior, tipo in etiquetas_anteriores.items():
                self.cambios += EquipoCentro.objects.filter(componente__centro=centro,
                    componente__tipo=tipo, categoria=anterior).update(categoria=str(dict(Componente.TIPOS)[tipo]))
            for datos in revision['gobierno']:
                previo, nuevo = datos['antes'], datos['despues']
                q = centro.gobierno.select_for_update()
                obj = q.filter(nombre=nuevo[0]).first() or q.filter(nombre=previo[0]).first()
                campos = ('nombre', 'rol', 'icono', 'responsabilidad', 'funciones')
                if obj:
                    self.actualizar(obj, {'antes': dict(zip(campos, previo)), 'despues': dict(zip(campos, nuevo))})
            for datos in revision['articulacion']:
                previo, nuevo = datos['antes'], datos['despues']
                q = centro.articulaciones.select_for_update().filter(tipo='carrera')
                obj = q.filter(actor=previo[1]).first()
                if obj and not q.filter(actor=nuevo[1]).exclude(pk=obj.pk).exists():
                    self.actualizar(obj, {'antes': {'actor': previo[1]}, 'despues': {'actor': nuevo[1]}})
            for datos in revision['ruta']:
                previo, nuevo = datos['antes'], datos['despues']
                obj = centro.ruta.select_for_update().filter(numero=previo[0]).first()
                if obj:
                    self.actualizar(obj, {'antes': {'responsable': previo[3]}, 'despues': {'responsable': nuevo[3]}})
            for datos in revision['modalidades']:
                previo, nuevo = datos['antes'], datos['despues']
                q = centro.modalidades.select_for_update()
                obj = q.filter(nombre=nuevo[0]).first() or q.filter(nombre=previo[0]).first()
                if obj:
                    campos = ('nombre', 'proposito', 'usuarios', 'icono')
                    self.actualizar(obj, {'antes': dict(zip(campos, previo)), 'despues': dict(zip(campos, nuevo))})
            for orden, (tipo, actor, forma, slug) in enumerate(cidt.ARTICULACION, 1):
                if tipo == 'carrera' and not centro.articulaciones.filter(tipo=tipo, actor=actor).exists():
                    obj = Articulacion(centro=centro, tipo=tipo, actor=actor, forma=forma, unidad_slug=slug, orden=orden)
                    obj.full_clean()
                    obj.save()
                    self.cambios += 1
            for orden, (linea, codigo, nombre, descripcion, entregable) in enumerate(revision['servicios_nuevos'], 200):
                if not centro.servicios.filter(nombre=nombre).exists():
                    obj = Servicio(centro=centro, componente=areas[codigo], nombre=nombre, linea=linea,
                        descripcion=descripcion, entregable=entregable, orden=orden,
                        **cidt.DETALLES_SERVICIOS[nombre])
                    obj.full_clean()
                    obj.save()
                    self.cambios += 1
            for nombre in revision['servicios_transversales']:
                obj = centro.servicios.select_for_update().filter(nombre=nombre).first()
                if obj:
                    valores = cidt.DETALLES_SERVICIOS[nombre]
                    self.actualizar(obj, {'antes': dict.fromkeys(valores, ''), 'despues': valores})
            if not options['aplicar']:
                transaction.set_rollback(True, using=alias)
        modo = 'Aplicados' if options['aplicar'] else 'Previstos; transacción revertida'
        self.stdout.write(f'{modo}: {self.cambios} registros; {len(self.conflictos)} campos manuales conservados.')
        for nombre in self.conflictos:
            self.stdout.write('Conservado: ' + nombre)

    def actualizar(self, obj, datos):
        campos = []
        for campo, nuevo in datos['despues'].items():
            actual = getattr(obj, campo)
            if actual == nuevo:
                continue
            if actual in ('', None) or actual == datos['antes'].get(campo):
                setattr(obj, campo, nuevo)
                campos.append(campo)
            else:
                self.conflictos.append(f'{obj._meta.model_name}:{obj.pk}.{campo}')
        if campos:
            obj.full_clean()
            obj.save(update_fields=campos)
            self.cambios += 1

    def proceso(self, area, datos):
        if area.flujo != datos['despues']['flujo']:
            return  # Un flujo manual no se sustituye indirectamente mediante sus pasos.
        nombre, entrada, salida = datos['proceso_anterior']
        proceso = ProcesoArea.objects.select_for_update().filter(componente=area, nombre=nombre).first()
        if proceso is None:
            # Un proceso renombrado por el gestor conserva también sus pasos.
            self.conflictos.append(f'componente:{area.pk}.proceso')
            return
        anteriores = pares_de(datos['pasos_anteriores'])
        nuevos = pares_de(datos['despues']['flujo'])
        for numero, (titulo, descripcion) in enumerate(nuevos, 1):
            paso = proceso.pasos.select_for_update().filter(numero=numero).first()
            if paso:
                anterior = anteriores[numero - 1] if numero <= len(anteriores) else ('', '')
                anterior = (re.sub(r'^\d+\.\s*', '', anterior[0])[:160], anterior[1])
                self.actualizar(paso, {'antes': dict(zip(('nombre', 'descripcion'), anterior)),
                    'despues': {'nombre': titulo, 'descripcion': descripcion}})
            else:
                paso = PasoProceso(proceso=proceso, numero=numero, nombre=titulo, descripcion=descripcion)
                paso.full_clean()
                paso.save()
                self.cambios += 1
