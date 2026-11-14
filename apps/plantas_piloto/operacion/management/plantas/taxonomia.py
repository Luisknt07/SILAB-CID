"""Taxonomía única de familias y productos para las cinco plantas piloto.

Los nombres proceden de ``Mapa_de_Contenidos_Plataforma_UPEC.xlsx``, hoja
``03_Taxonomia_Familias``. La escala de una receta se conserva aparte y no
forma parte del nombre que ve el público.
"""


PRODUCTOS_TAXONOMIA = {
    'LAC': {
        'Leches y fermentados': (
            ('Leche pasteurizada', 'litro'), ('Leche descremada', 'litro'),
            ('Yogur de mora', 'litro'),
        ),
        'Quesos': (
            ('Queso fresco', 'kg'), ('Queso mozzarella', 'kg'),
            ('Queso semimaduro', 'kg'), ('Queso maduro', 'kg'),
        ),
        'Cremas y mantequilla': (
            ('Crema de leche', 'litro'), ('Mantequilla', 'kg'), ('Mazada', 'litro'),
        ),
        'Dulces de leche': (('Manjar de leche', 'kg'), ('Arequipe', 'kg')),
        'Helados': (
            ('Helado de crema', 'kg'), ('Helado de yogur', 'kg'), ('Paletas', 'unidad'),
        ),
        'Derivados del suero': (
            ('Suero en polvo', 'kg'), ('Bebida de suero', 'litro'), ('Ricotta', 'kg'),
        ),
    },
    'CAR': {
        'Cortes y despiece': (
            ('Cortes de res', 'kg'), ('Cortes de cerdo', 'kg'),
            ('Cortes de ave', 'kg'), ('Carne molida', 'kg'),
        ),
        'Embutidos frescos': (
            ('Chorizo', 'kg'), ('Longaniza', 'kg'), ('Hamburguesa', 'kg'),
        ),
        'Embutidos escaldados': (
            ('Salchicha', 'kg'), ('Mortadela', 'kg'), ('Jamonada', 'kg'),
        ),
        'Curados y madurados': (
            ('Salami', 'kg'), ('Chorizo español', 'kg'), ('Cecina', 'kg'),
        ),
        'Cocidos y ahumados': (
            ('Jamón', 'kg'), ('Tocino', 'kg'), ('Costilla ahumada', 'kg'),
        ),
        'Platos preparados': (
            ('Apanados', 'kg'), ('Marinados', 'kg'), ('Listos para calentar', 'kg'),
        ),
    },
    'HOR': {
        'Pulpas y néctares': (
            ('Pulpa de mora', 'kg'), ('Pulpa de tomate de árbol', 'kg'), ('Néctares', 'litro'),
        ),
        'Mermeladas y confituras': (
            ('Mermelada de mora', 'kg'), ('Mermelada de mortiño', 'kg'),
            ('Mermelada de ají', 'kg'),
        ),
        'Conservas y encurtidos': (
            ('Duraznos en almíbar', 'kg'), ('Encurtidos', 'kg'), ('Salsas', 'kg'),
        ),
        'Deshidratados': (
            ('Fruta deshidratada', 'kg'), ('Hierbas deshidratadas', 'kg'), ('Hojuelas', 'kg'),
        ),
        'Congelados y IV gama': (
            ('Pulpa congelada', 'kg'), ('Hortaliza cortada', 'kg'), ('Producto IQF', 'kg'),
        ),
        'Extractos y aceites': (
            ('Extractos', 'litro'), ('Aceites esenciales', 'litro'),
            ('Colorantes naturales', 'kg'),
        ),
    },
    'ALM': {
        'Almidones nativos': (
            ('Almidón de papa', 'kg'), ('Almidón de yuca', 'kg'), ('Almidón de achira', 'kg'),
        ),
        'Almidones modificados': (
            ('Almidón pregelatinizado', 'kg'), ('Almidón acetilado', 'kg'),
            ('Almidón entrecruzado', 'kg'),
        ),
        'Harinas y premezclas': (
            ('Harina de quinua', 'kg'), ('Harina de chocho', 'kg'), ('Premezclas', 'kg'),
        ),
        'Snacks extruidos': (('Extruidos de maíz', 'kg'), ('Extruidos de quinua', 'kg')),
        'Fermentados alcohólicos': (
            ('Cerveza artesanal', 'litro'), ('Vino de frutas', 'litro'), ('Hidromiel', 'litro'),
        ),
        'Destilados': (
            ('Aguardiente', 'litro'), ('Licores compuestos', 'litro'), ('Macerados', 'litro'),
        ),
        'Vinagres': (('Vinagre de frutas', 'litro'), ('Vinagre de caña', 'litro')),
    },
    'PAN': {
        'Panes': (
            ('Pan de molde', 'unidad'), ('Pan integral', 'unidad'),
            ('Pan artesanal', 'unidad'), ('Pan andino', 'unidad'),
        ),
        'Bollería y pastelería': (
            ('Bizcochos', 'unidad'), ('Tortas', 'unidad'), ('Postres', 'unidad'),
        ),
        'Galletería': (
            ('Galletas dulces', 'unidad'), ('Galletas saladas', 'unidad'),
            ('Galletas con harinas andinas', 'unidad'),
        ),
        'Masas congeladas': (
            ('Masa de pan congelada', 'kg'), ('Masa de hojaldre congelada', 'kg'),
            ('Masa prefermentada congelada', 'kg'),
        ),
        'Productos sin gluten': (
            ('Pan sin gluten', 'unidad'), ('Galleta sin gluten', 'unidad'),
            ('Premezcla sin gluten', 'kg'),
        ),
        'Snacks horneados': (('Palitos', 'kg'), ('Tostadas', 'kg'), ('Crocantes', 'kg')),
    },
}


TAXONOMIA_FAMILIAS = {
    prefijo: tuple(familias)
    for prefijo, familias in PRODUCTOS_TAXONOMIA.items()
}
