"""Amplía café conservando ids, relaciones y ediciones posteriores a la carga."""

import hashlib
import json
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import CommandError
from django.db.models import F

from apps.gestion_unidades.models.espacios import EspacioReservable
from apps.gestion_unidades.models.fichas import FichaContenido
from apps.gestion_unidades.models.fichas_area import ElementoFichaArea, FichaArea
from apps.plantas_piloto.operacion.management.commands.preparar_planta_cafe import (
    Command as BaseCafe,
)
from apps.plantas_piloto.operacion.management.plantas.cafe import (
    ALCANCE,
    PRODUCTOS,
    PROCESOS as BASE,
)
from apps.plantas_piloto.operacion.management.plantas.cafe_cadena import (
    ADICIONES_INSUMOS,
    ADICIONES_PRODUCTOS,
    PROCESOS,
)
from apps.plantas_piloto.operacion.management.plantas.cafe_equipos import (
    AREAS,
    EQUIPOS,
    ZONAS,
)
from apps.plantas_piloto.operacion.models.produccion import (
    EtapaReceta,
    FamiliaProducto,
    InsumoReceta,
    Producto,
    Receta,
)
from apps.recursos.models.consumibles import Consumible

MARCA = "CAF-LINEA v2;sha256:"
FICHA_CAMPOS = (
    "que_es",
    "como_funciona",
    "principio",
    "distribucion",
    "aplicaciones",
    "conexiones",
    "seguridad",
    "publicada",
)
ELEMENTO_CAMPOS = (
    "nombre",
    "tipo",
    "nivel",
    "icono",
    "para_que",
    "ejemplo",
    "cantidad",
    "especificaciones",
    "consumibles",
    "cuidados",
    "url",
    "orden",
    "registrado_id",
    "insumo_registrado_id",
    "software_registrado_id",
    "imagen_estatica",
    "foto",
)
ETAPA_CAMPOS = (
    "orden",
    "nombre",
    "tipo",
    "duracion_min",
    "espera_min",
    "personas",
    "rendimiento_pct",
    "distancia_m",
    "punto_critico",
    "punto_control",
    "parametro",
    "limite",
    "instrucciones",
)


def normal(valor):
    if isinstance(valor, bool) or valor is None:
        return valor
    if isinstance(valor, (int, Decimal)):
        return format(Decimal(valor).normalize(), "f")
    if isinstance(valor, dict):
        return {k: normal(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [normal(v) for v in valor]
    return valor


def huella(valores):
    return hashlib.sha256(
        json.dumps(normal(valores), ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def campos(objeto, nombres):
    return {
        n: getattr(objeto, n).name if n == "foto" else getattr(objeto, n)
        for n in nombres
    }


def firma_receta(receta):
    return {
        "campos": campos(
            receta,
            (
                "nombre",
                "cantidad_base",
                "unidad_base",
                "rendimiento_esperado",
                "duracion_horas",
                "instrucciones",
                "origen",
                "activa",
                "responsable_id",
                "derivado_de_id",
            ),
        ),
        "producto": receta.producto.codigo,
        "etapas": [
            {
                **campos(e, ETAPA_CAMPOS),
                "area": e.espacio.codigo if e.espacio_id else None,
                "equipo": e.equipo_id,
            }
            for e in receta.etapas.select_related("espacio").order_by("orden")
        ],
        "insumos": sorted(
            [
                (
                    i.consumible.codigo,
                    i.cantidad,
                    i.forma_parte,
                    i.obligatorio,
                    i.etapa.orden if i.etapa_id else None,
                )
                for i in receta.insumos.select_related("consumible", "etapa")
            ]
        ),
        "salidas": list(
            receta.salidas.values_list(
                "producto_id", "cantidad", "etapa_id", "externa_al_flujo"
            )
        ),
        "software": list(receta.software.order_by("pk").values_list("pk", flat=True)),
    }


def firma_base(datos, nombres):
    etapas = []
    for orden, paso in enumerate(datos["etapas"], 1):
        modelo = EtapaReceta(
            **{k: v for k, v in paso.items() if k != "area"}, orden=orden
        )
        modelo.rendimiento_pct = Decimal(paso["rendimiento_pct"]).quantize(
            Decimal(".01")
        )
        etapas.append(
            {**campos(modelo, ETAPA_CAMPOS), "area": paso["area"], "equipo": None}
        )
    receta = Receta(
        nombre=nombres[datos["producto"]],
        cantidad_base=Decimal(datos["base"]),
        unidad_base="kg",
        rendimiento_esperado=Decimal(datos["salida"]),
        instrucciones=datos["instrucciones"],
    )
    return {
        "campos": campos(
            receta,
            (
                "nombre",
                "cantidad_base",
                "unidad_base",
                "rendimiento_esperado",
                "duracion_horas",
                "instrucciones",
                "origen",
                "activa",
                "responsable_id",
                "derivado_de_id",
            ),
        ),
        "producto": "CAF-P-" + datos["producto"],
        "etapas": etapas,
        "insumos": sorted(
            [("CAF-I-" + datos["insumo"], Decimal(datos["base"]), "base", True, 1)]
            + [
                ("CAF-I-" + c, Decimal(q), "no", True, len(etapas) - 1)
                for c, q in datos["empaques"]
            ]
        ),
        "salidas": [],
        "software": [],
    }


class Command(BaseCafe):
    help = "Completa equipamiento individual, laboratorio de calidad y línea de café de 250/500/1.000 g."

    def cargar(self, unidad):
        areas = {a.codigo: a for a in EspacioReservable.objects.filter(unidad=unidad)}
        for orden, (codigo, (nombre, pasos)) in enumerate(AREAS.items(), 1):
            if codigo not in areas:
                areas[codigo], _ = self.obtener(
                    EspacioReservable,
                    {"unidad": unidad, "codigo": codigo},
                    dict(
                        nombre=nombre,
                        orden=orden,
                        reservable=False,
                        descripcion_publica="Zona funcional de la cadena de café; confirmar ubicación, aforo y recursos antes de habilitar reservas.",
                        caracteristicas="Distribución funcional definida para la cadena. Aforo y capacidad técnica pendientes de levantamiento.",
                    ),
                )
        # La carga inicial conserva su contrato; esta revisión amplía sólo sus referencias reconocidas.
        super().cargar(unidad)
        base_fichas, base_elementos = self.baseline_areas(areas)
        fichas = {}
        for codigo, (nombre, pasos) in AREAS.items():
            ficha = (
                FichaArea.objects.filter(espacio=areas[codigo]).first()
                if areas[codigo].pk
                else None
            )
            valores = dict(
                que_es="Zona de "
                + nombre
                + " en la cadena de café de finca: recepción, transformación y decisiones documentadas.",
                como_funciona="\n\n".join(t + ": " + d for t, d in pasos)
                + "\nLa información describe funciones y equipos; los activos y aforos se verifican en inventario antes de operar.",
                principio="\n".join(t + " | " + d for t, d in pasos),
                distribucion="\n".join(
                    t
                    + " | "
                    + d
                    + " | "
                    + "; ".join(
                        e["nombre"] for e in EQUIPOS if e["clave"] in ZONAS[codigo][i]
                    )
                    for i, (t, d) in enumerate(pasos)
                ),
                aplicaciones="Recepción y control de microlotes\nPrácticas con guía y evidencia\nComparación de rutas y perfiles\nServicios autorizados y mejora de rendimiento",
                conexiones="Flujo de café y personas segregado\nAgua, energía, extracción y drenajes según equipo real\nIntercambio de muestras con laboratorio de calidad\nTrazabilidad y registros por lote",
                seguridad="Inducción y supervisión\nResguardos y bloqueo para limpieza/mantenimiento\nControl de calor, polvo, gas, agua y cargas\nRetención de no conformes y manejo de residuos",
                publicada=True,
            )
            if ficha is None:
                ficha, _ = self.obtener(
                    FichaArea,
                    {"espacio": areas[codigo]},
                    dict(**valores, fuente=MARCA + huella(valores)),
                )
            else:
                actual = campos(ficha, FICHA_CAMPOS)
                propio = ficha.fuente == MARCA + huella(actual)
                anterior = codigo in base_fichas and huella(actual) == huella(
                    campos(base_fichas[codigo], FICHA_CAMPOS)
                )
                if (propio or anterior) and actual != valores:
                    self.resumen["Fichas ampliadas"] += 1
                    if self.aplicar:
                        for k, v in valores.items():
                            setattr(ficha, k, v)
                        ficha.fuente = MARCA + huella(valores)
                        ficha.full_clean()
                        ficha.save()
                elif not propio and not anterior:
                    self.resumen["Fichas editadas conservadas"] += 1
            fichas[codigo] = ficha
        for orden, equipo in enumerate(EQUIPOS, 1):
            self.equipo(unidad, equipo, orden, fichas, base_elementos)
        for (
            clave,
            familia,
            nombre,
            tipo,
            presentacion,
            descripcion,
        ) in ADICIONES_PRODUCTOS:
            producto, creado = self.obtener(
                Producto,
                {"codigo": "CAF-P-" + clave},
                dict(
                    unidad=unidad,
                    familia=FamiliaProducto.objects.get(
                        unidad=unidad, codigo="CAF-F-" + familia
                    )
                    if self.aplicar
                    or FamiliaProducto.objects.filter(
                        unidad=unidad, codigo="CAF-F-" + familia
                    ).exists()
                    else None,
                    nombre=nombre,
                    tipo=tipo,
                    unidad_medida="kg",
                    presentacion=presentacion,
                    descripcion=descripcion + "\n\n" + ALCANCE,
                ),
            )
            if creado:
                self.editorial(producto, "producto")
        for clave, nombre, medida, clase, especificacion in ADICIONES_INSUMOS:
            self.obtener(
                Consumible,
                {"codigo": "CAF-I-" + clave},
                dict(
                    unidad=unidad,
                    nombre=nombre,
                    unidad_medida=medida,
                    clasificacion=clase,
                    especificacion_tecnica=especificacion,
                    descripcion=especificacion,
                    stock_total=0,
                ),
            )
        nombres = {p[0]: p[2] for p in PRODUCTOS}
        originales = {p["clave"]: firma_base(p, nombres) for p in BASE}
        for proceso in PROCESOS:
            self.proceso(unidad, proceso, areas, originales)

    @staticmethod
    def baseline_areas(areas):
        """Reconstruye valores públicos de v1 desde su código, sin leer datos privados ni escribir."""
        fichas, elementos = {}, {}
        cargador = BaseCafe()

        def recoger(modelo, filtro, valores):
            obj = modelo(**filtro, **valores)
            if modelo is FichaArea:
                fichas[obj.espacio.codigo] = obj
            if modelo is ElementoFichaArea:
                elementos[obj.nombre] = obj
            return obj, True

        cargador.obtener = recoger
        cargador.areas(areas)
        return fichas, elementos

    def indice(self, unidad, objeto, codigo, tipo, titulo, firma):
        if not self.aplicar:
            return None
        ct = ContentType.objects.get_for_model(objeto)
        indice = FichaContenido.objects.filter(
            content_type=ct, object_id=objeto.pk
        ).first()
        if indice is None:
            indice = FichaContenido(
                unidad=unidad,
                codigo=codigo,
                tipo=tipo,
                titulo=titulo,
                descripcion="Ficha técnica de referencia; existencia y operación requieren comprobación.",
                content_type=ct,
                object_id=objeto.pk,
                estado="publicada",
                visibilidad="publica",
            )
        indice.observacion_validacion = MARCA + huella(firma)
        indice.version = 2
        indice.full_clean()
        indice.save()
        return indice

    def equipo(self, unidad, datos, orden, fichas, originales):
        codigo = "CAF-REF-" + datos["clave"]
        indice = FichaContenido.objects.filter(unidad=unidad, codigo=codigo).first()
        obj = indice.objeto if indice else None
        if indice and not isinstance(obj, ElementoFichaArea):
            raise CommandError(
                "El código de referencia apunta a otro tipo de objeto: " + codigo
            )
        if obj is None and datos["alias"]:
            obj = ElementoFichaArea.objects.filter(
                ficha__espacio__unidad=unidad, nombre=datos["alias"], tipo="equipo"
            ).first()
        valores = dict(
            nombre=datos["nombre"],
            tipo="equipo",
            nivel=datos["nivel"],
            icono="fas fa-coffee",
            para_que=datos["para_que"],
            ejemplo="Ficha CAF-REF-"
            + datos["clave"]
            + " · marca/modelo e instalación por verificar",
            cantidad="Según levantamiento y prueba de la unidad",
            especificaciones=datos["especificaciones"],
            consumibles=datos["consumibles"],
            cuidados=datos["cuidados"],
            url=datos["url"],
            orden=orden,
            registrado_id=None,
            insumo_registrado_id=None,
            software_registrado_id=None,
            imagen_estatica="",
            foto="",
        )
        destino = fichas[datos["area"]]
        if obj is None:
            obj, _ = self.obtener(
                ElementoFichaArea,
                {"ficha": destino, "nombre": valores.pop("nombre")},
                valores,
            )
        else:
            actual = {**campos(obj, ELEMENTO_CAMPOS), "area": obj.ficha.espacio.codigo}
            original = originales.get(datos["alias"])
            anterior = original is not None and huella(actual) == huella(
                {
                    **campos(original, ELEMENTO_CAMPOS),
                    "area": original.ficha.espacio.codigo,
                }
            )
            propio = indice and indice.observacion_validacion == MARCA + huella(actual)
            if not anterior and not propio:
                self.resumen["Equipos editados conservados"] += 1
                return
            deseado = {**valores, "area": datos["area"]}
            if huella(actual) == huella(deseado):
                return
            self.resumen["Equipos ampliados"] += 1
            if self.aplicar:
                for k, v in valores.items():
                    setattr(obj, k, v)
                obj.ficha = destino
                obj.full_clean()
                obj.save()
        self.indice(
            unidad,
            obj,
            codigo,
            "equipo",
            datos["nombre"],
            {**campos(obj, ELEMENTO_CAMPOS), "area": datos["area"]},
        )

    def proceso(self, unidad, datos, areas, originales):
        qs = Receta.objects.filter(unidad=unidad, codigo="CAF-R-" + datos["clave"])
        receta = qs.select_for_update().first() if self.aplicar else qs.first()
        nuevo = receta is None
        if receta:
            actual = firma_receta(receta)
            indice = FichaContenido.objects.filter(
                unidad=unidad, object_id=receta.pk, tipo="proceso"
            ).first()
            propio = indice and indice.observacion_validacion == MARCA + huella(actual)
            if (
                indice
                and (
                    indice.decision_editorial_manual
                    or indice.estado_validacion != "pendiente"
                )
            ) or (
                huella(actual) != huella(originales.get(datos["clave"])) and not propio
            ):
                self.resumen["Procesos editados conservados"] += 1
                return
        producto = Producto.objects.filter(
            unidad=unidad, codigo="CAF-P-" + datos["producto"]
        ).first()
        if not self.aplicar and producto is None:
            self.resumen["Receta"] += 1
            return
        if nuevo:
            receta, _ = self.obtener(
                Receta,
                {"codigo": "CAF-R-" + datos["clave"]},
                dict(
                    unidad=unidad,
                    producto=producto,
                    familia=producto.familia,
                    nombre=producto.nombre,
                    cantidad_base=Decimal(datos["base"]),
                    unidad_base="kg",
                    rendimiento_esperado=Decimal(datos["salida"]),
                    instrucciones=datos["instrucciones"],
                ),
            )
            self.editorial(receta, "proceso")
        actuales = list(receta.etapas.all()) if receta.pk else []
        por_nombre = {e.nombre: e for e in actuales}
        usados, plan = set(), []
        for orden, dato in enumerate(datos["etapas"], 1):
            obj = por_nombre.get(dato["nombre"]) or por_nombre.get(dato.get("alias"))
            if obj:
                usados.add(obj.pk)
            valores = {k: v for k, v in dato.items() if k not in ("area", "alias")}
            valores["rendimiento_pct"] = Decimal(valores["rendimiento_pct"]).quantize(
                Decimal(".01")
            )
            plan.append((obj, orden, valores, areas[dato["area"]]))
        if set(e.pk for e in actuales) - usados:
            raise CommandError(
                "La revisión dejaría etapas previas sin correspondencia; no se retiran: "
                + receta.codigo
            )
        cambiado = (
            nuevo
            or receta.instrucciones != datos["instrucciones"]
            or len(actuales) != len(plan)
        )
        for obj, orden, vals, area in plan:
            cambiado |= (
                obj is None
                or any(getattr(obj, k) != v for k, v in vals.items())
                or (obj and (obj.orden != orden or obj.espacio_id != area.pk))
            )
        if not cambiado:
            return
        self.resumen["Procesos ampliados"] += 1
        if not self.aplicar:
            return
        receta.instrucciones = datos["instrucciones"]
        receta.save(update_fields=["instrucciones", "actualizado_en"])
        # Orden temporal sólo en esta transacción, sin borrar etapas ni sus relaciones.
        receta.etapas.update(orden=F("orden") + 5000)
        etapas = []
        for obj, orden, valores, area in plan:
            obj = obj or EtapaReceta(receta=receta, familia=receta.familia)
            for k, v in valores.items():
                setattr(obj, k, v)
            obj.orden, obj.espacio = orden, area
            obj.full_clean()
            obj.save()
            etapas.append(obj)
        base = Consumible.objects.get(unidad=unidad, codigo="CAF-I-" + datos["insumo"])
        InsumoReceta.objects.update_or_create(
            receta=receta,
            consumible=base,
            defaults={
                "cantidad": Decimal(datos["base"]),
                "forma_parte": "base",
                "etapa": etapas[0],
            },
        )
        for clave, cantidad in datos["empaques"]:
            material = Consumible.objects.get(unidad=unidad, codigo="CAF-I-" + clave)
            InsumoReceta.objects.update_or_create(
                receta=receta,
                consumible=material,
                defaults={
                    "cantidad": Decimal(cantidad),
                    "forma_parte": "no",
                    "etapa": etapas[-4],
                },
            )
        self.indice(
            unidad,
            receta,
            "CAF-F-" + receta.codigo,
            "proceso",
            receta.nombre,
            firma_receta(receta),
        )
