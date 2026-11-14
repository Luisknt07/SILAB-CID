"""Diagramas originales del aula: SVG accesible y PNG equivalente para PDF.

Ejecutar desde cualquier carpeta; requiere Pillow. No se ejecuta en peticiones web.
"""

from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parents[3] / "static/portal/img/cursos/logistica-ia"
W, H = 1200, 760
C = {
    "bg": "#f2f7f5",
    "ink": "#122d2a",
    "muted": "#4c6662",
    "green": "#24623c",
    "teal": "#087c87",
    "blue": "#3266af",
    "purple": "#7451ac",
    "gold": "#e2ae29",
    "red": "#b84e55",
    "line": "#d4e1db",
}


class Scene:
    def __init__(self, title, description):
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760" role="img" aria-labelledby="titulo descripcion"><title id="titulo">{escape(title)}</title><desc id="descripcion">{escape(description)}</desc>'
        ]
        self.im = Image.new("RGB", (W, H), C["bg"])
        self.d = ImageDraw.Draw(self.im)

    def rect(self, x, y, w, h, fill, stroke=None, r=18):
        self.svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"'
            + (f' stroke="{stroke}" stroke-width="2"' if stroke else "")
            + "/>"
        )
        self.d.rounded_rectangle(
            (x, y, x + w, y + h), r, fill=fill, outline=stroke, width=2
        )

    def line(self, x1, y1, x2, y2, color, width=3):
        self.svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
        )
        self.d.line((x1, y1, x2, y2), fill=color, width=width)

    def circle(self, x, y, r, fill):
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>')
        self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)

    def text(self, x, y, text, size=24, color=None, bold=False, maxwidth=None):
        color = color or C["ink"]
        fuentes = [
            Path(
                "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
            ),
            Path(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ),
        ]
        fuente = next((ruta for ruta in fuentes if ruta.exists()), None)
        font = (
            ImageFont.truetype(str(fuente), size)
            if fuente
            else ImageFont.load_default(size=size)
        )
        lines = [""]
        for word in text.split():
            if (
                maxwidth
                and lines[-1]
                and font.getlength(lines[-1] + " " + word) > maxwidth
            ):
                lines.append(word)
            else:
                lines[-1] = (lines[-1] + " " + word).strip()
        for n, line in enumerate(lines):
            yy = y + n * round(size * 1.35)
            self.svg.append(
                f'<text x="{x}" y="{yy + size}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(line)}</text>'
            )
            self.d.text((x, yy), line, font=font, fill=color)
        return len(lines) * round(size * 1.35)

    def arrow(self, x1, y1, x2, y2, color=None):
        color = color or C["green"]
        self.line(x1, y1, x2, y2, color, 4)
        if abs(x2 - x1) >= abs(y2 - y1):
            points = [(x2, y2), (x2 - 12, y2 - 7), (x2 - 12, y2 + 7)]
        else:
            points = [(x2, y2), (x2 - 7, y2 - 12), (x2 + 7, y2 - 12)]
        self.svg.append(
            '<polygon points="'
            + " ".join(f"{x},{y}" for x, y in points)
            + '" fill="'
            + color
            + '"/>'
        )
        self.d.polygon(points, fill=color)

    def header(self, kicker, title, subtitle):
        self.rect(0, 0, W, 144, C["ink"], r=0)
        self.text(42, 20, kicker.upper(), 18, "#ffda50", True)
        self.text(42, 51, title, 34, "#ffffff", True, maxwidth=1110)
        self.text(42, 111, subtitle, 20, "#c9ded6", maxwidth=1110)

    def card(self, x, y, w, h, num, title, body, color):
        self.rect(x, y, w, h, "#ffffff", C["line"])
        self.rect(x, y, 8, h, color, r=3)
        self.circle(x + 40, y + 40, 21, color)
        self.text(x + 31, y + 23, str(num), 23, "#ffffff", True)
        self.text(x + 75, y + 20, title, 25, color, True, maxwidth=w - 96)
        self.text(x + 24, y + 86, body, 23, maxwidth=w - 48)

    def footer(
        self,
        text="Caso docente Andina Distribución · Datos ficticios · Aprende, prueba y comprueba",
    ):
        self.line(40, 704, 1160, 704, C["line"], 2)
        self.text(42, 721, text, 18, C["muted"])

    def save(self, name):
        self.svg.append("</svg>")
        (BASE / (name + ".svg")).write_text("\n".join(self.svg), encoding="utf-8")
        self.im.save(BASE / (name + ".png"), optimize=True)


def base(name, title, subtitle):
    s = Scene(title, subtitle)
    s.header("Aplicaciones logísticas con IA", title, subtitle)
    return s


def generar():
    BASE.mkdir(parents=True, exist_ok=True)
    s = base(
        "ruta-curso",
        "Tu ruta en cinco unidades",
        "40 horas obligatorias · Un mismo caso de inventario, de principio a fin",
    )
    s.card(
        40,
        180,
        350,
        215,
        1,
        "Diseña",
        "Define el problema, el usuario y las reglas antes de pedir código.",
        C["green"],
    )
    s.card(
        425,
        180,
        350,
        215,
        2,
        "Arranca",
        "Prepara el kit y aprende a pedir cambios pequeños a la IA.",
        C["teal"],
    )
    s.card(
        810,
        180,
        350,
        215,
        3,
        "Construye",
        "Registra entradas y salidas; prueba datos y permisos.",
        C["blue"],
    )
    s.arrow(393, 287, 420, 287)
    s.arrow(778, 287, 805, 287)
    s.card(
        235,
        433,
        350,
        215,
        4,
        "Conecta",
        "Comprueba indicadores y consulta con MCP de solo lectura.",
        C["purple"],
    )
    s.card(
        620,
        433,
        350,
        215,
        5,
        "Demuestra",
        "Corrige, documenta y presenta tu aplicación con evidencias.",
        C["green"],
    )
    s.arrow(588, 540, 615, 540)
    s.footer()
    s.save("ruta-curso")
    s = base(
        "flujo-inventario",
        "Una operación, una comprobación",
        "La pantalla informa; el servidor valida; el historial deja evidencia",
    )
    for x, num, title, body, color in [
        (40, 1, "Producto", "Un código único y una unidad definida.", C["green"]),
        (425, 2, "Movimiento", "Entrada o salida, cantidad y motivo.", C["teal"]),
        (
            810,
            3,
            "Validación",
            "Permiso, cantidad positiva y saldo suficiente.",
            C["blue"],
        ),
    ]:
        s.card(x, 190, 350, 210, num, title, body, color)
    s.arrow(393, 294, 420, 294)
    s.arrow(778, 294, 805, 294)
    s.card(
        235,
        445,
        350,
        205,
        4,
        "Guardar juntos",
        "Saldo e historial cambian en una misma operación.",
        C["purple"],
    )
    s.card(
        620,
        445,
        350,
        205,
        5,
        "Verificar",
        "Compara mensaje, existencia e historial.",
        C["green"],
    )
    s.arrow(588, 547, 615, 547)
    s.footer()
    s.save("flujo-inventario")
    s = base(
        "mapa-proyecto",
        "Reconoce el kit sin memorizar código",
        "Cada archivo tiene una tarea; pregunta qué cambia y por qué",
    )
    items = [
        ("manage.py", "Arranca el servidor y ejecuta tareas."),
        ("models.py", "Describe productos y movimientos."),
        ("forms.py", "Recibe campos y muestra errores."),
        ("services.py", "Aplica reglas y registra operaciones."),
        ("views.py", "Responde a cada solicitud."),
        ("templates / tests.py", "Muestra pantallas y comprueba reglas."),
    ]
    for i, (title, body) in enumerate(items):
        s.card(
            40 + (i % 3) * 385,
            180 + (i // 3) * 250,
            350,
            220,
            i + 1,
            title,
            body,
            [C["green"], C["teal"], C["blue"], C["purple"], C["teal"], C["green"]][i],
        )
    s.footer()
    s.save("mapa-proyecto")
    s = base(
        "ciclo-ia",
        "Trabaja con IA en cambios pequeños",
        "La respuesta del asistente se acepta después de comprobarla",
    )
    items = [
        ("1. Define", "Una necesidad y una prueba concreta."),
        ("2. Planifica", "Revisa qué archivos cambiaría."),
        ("3. Modifica", "Acepta una mejora cada vez."),
        ("4. Comprueba", "Prueba desde la pantalla y con tests."),
        ("5. Decide", "Conserva el cambio o vuelve atrás."),
        ("6. Registra", "Guarda la versión y la evidencia."),
    ]
    for i, (title, body) in enumerate(items):
        s.card(
            40 + (i % 3) * 385,
            180 + (i // 3) * 250,
            350,
            220,
            i + 1,
            title,
            body,
            [C["green"], C["teal"], C["blue"], C["purple"], C["green"], C["teal"]][i],
        )
    s.footer(
        "La cantidad de código no es la meta: explica qué cambió y cómo sabes que funciona."
    )
    s.save("ciclo-ia")
    s = base(
        "regla-stock",
        "Comprueba el saldo con un ejemplo",
        "Producto de prueba independiente · Todas las cantidades en la misma unidad",
    )
    for i, (title, body, color) in enumerate(
        [
            ("Entrada 10", "Saldo: 10.00 | Historial: 1 movimiento", C["green"]),
            ("Salida 3", "Saldo: 7.00 | Historial: 2 movimientos", C["teal"]),
            (
                "Intento salida 8",
                "RECHAZADA | Saldo: 7.00 | Historial: 2 movimientos",
                C["red"],
            ),
        ]
    ):
        s.card(60, 180 + i * 160, 1080, 140, i + 1, title, body, color)
    s.footer(
        "Una operación rechazada conserva la existencia y no agrega un movimiento."
    )
    s.save("regla-stock")
    s = base(
        "datos-indicadores",
        "Tres indicadores con significado claro",
        "Cuenta productos; evita sumar kilogramos, cajas y unidades como si fueran iguales",
    )
    s.card(
        40,
        190,
        350,
        255,
        1,
        "Productos",
        "Número de registros del catálogo. Ejemplo demo: 4.",
        C["green"],
    )
    s.card(
        425,
        190,
        350,
        255,
        2,
        "Bajo mínimo",
        "Existencia menor al mínimo. Ejemplo demo: 2.",
        C["teal"],
    )
    s.card(
        810,
        190,
        350,
        255,
        3,
        "Sin stock",
        "Existencia igual a cero. Ejemplo demo: 0.",
        C["blue"],
    )
    s.rect(65, 490, 1070, 160, "#fff4cc", "#e7c96c")
    s.text(90, 510, "Antes de importar un CSV", 26, C["ink"], True)
    s.text(
        90,
        558,
        "codigo, nombre, unidad, minimo. Revisa encabezados y errores; el kit rechaza el archivo completo si una fila es inválida.",
        24,
        maxwidth=1010,
    )
    s.footer()
    s.save("datos-indicadores")
    s = base(
        "arquitectura-mcp",
        "MCP: consulta datos, después comprueba",
        "Dos herramientas preparadas; ninguna registra salidas ni modifica inventario",
    )
    items = [
        ("Persona", "Pide una consulta de existencias."),
        ("Asistente + cliente", "Solicita la herramienta disponible."),
        ("Servidor MCP", "Recibe parámetros y consulta datos."),
        ("Base docente", "Devuelve códigos y cantidades."),
    ]
    for i, (title, body) in enumerate(items):
        s.card(
            40 + i * 290,
            195,
            260,
            250,
            i + 1,
            title,
            body,
            [C["green"], C["teal"], C["blue"], C["purple"]][i],
        )
    for i in range(3):
        s.arrow(304 + i * 290, 320, 326 + i * 290, 320)
    s.rect(65, 490, 1070, 160, "#e4f2ed", "#a6cbbb")
    s.text(90, 510, "Herramientas del kit", 26, C["green"], True)
    s.text(
        90, 555, "consultar_existencias  |  productos_bajo_minimo", 25, C["ink"], True
    )
    s.text(
        90,
        597,
        "Compara la respuesta con el tablero y confirma que el historial no cambió.",
        23,
        maxwidth=1010,
    )
    s.footer()
    s.save("arquitectura-mcp")
    s = base(
        "pruebas-entrega",
        "Antes de entregar, recorre esta ruta",
        "Un prototipo comprensible y comprobado vale más que una lista larga de funciones",
    )
    items = [
        ("Funciona", "Entrada y salida válida dan el saldo esperado."),
        ("Rechaza", "Duplicados, cantidades inválidas y exceso de salida."),
        ("Protege", "Consulta puede leer; no puede registrar."),
        ("Coincide", "CSV, tablero y MCP muestran datos verificables."),
        ("Se reproduce", "Otra persona puede seguir tu guía de arranque."),
        ("Se explica", "Demuestra el caso, una corrección y sus límites."),
    ]
    for i, (title, body) in enumerate(items):
        s.card(
            40 + (i % 3) * 385,
            180 + (i // 3) * 250,
            350,
            220,
            i + 1,
            title,
            body,
            [C["green"], C["red"], C["blue"], C["teal"], C["purple"], C["green"]][i],
        )
    s.footer(
        "Cuestionarios y entregas: mínimo 70/100. Las entregas necesitan revisión docente."
    )
    s.save("pruebas-entrega")
    print("8 diagramas SVG y sus 8 versiones PNG generados.")


if __name__ == "__main__":
    generar()
