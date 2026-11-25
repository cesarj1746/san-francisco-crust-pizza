"""Estructura esperada de las tres bases (según los archivos originales de la empresa)."""

VENTAS_REQ = ["VentaID", "Fecha", "Ciudad", "Sucursal", "ClienteID", "ProductoID", "Cantidad",
              "PrecioUnitario", "CostoUnitario", "DescuentoPct", "VentaNeta", "CostoTotal",
              "UtilidadBruta", "Canal", "FormaPago"]
VENTAS_OPC = ["Año", "Mes", "Trimestre", "TiempoEntregaMin", "TiempoPreparacionMin"]
VENTAS_NUM = ["Cantidad", "PrecioUnitario", "CostoUnitario", "DescuentoPct", "VentaNeta",
              "CostoTotal", "UtilidadBruta"]

CLIENTES_REQ = ["ClienteID", "Segmento"]
CLIENTES_OPC = ["Nombre", "Sexo", "Edad", "Ciudad", "FechaRegistro", "UltimaCompra",
                "TotalCompras", "GastoAcumuladoUSD", "TicketPromedioUSD", "CanalFavorito",
                "FrecuenciaCompraMensual", "ClienteActivo", "NPS", "MotivoPerdida"]

PRODUCTOS_REQ = ["ProductoID", "Categoria", "Producto"]
PRODUCTOS_OPC = ["Tamaño", "CostoUSD", "PrecioVentaUSD", "MargenBrutoUSD", "MargenPorcentaje",
                 "Activo"]

ESQUEMAS = {
    "ventas": (VENTAS_REQ, VENTAS_OPC, "VentaID"),
    "clientes": (CLIENTES_REQ, CLIENTES_OPC, "ClienteID"),
    "productos": (PRODUCTOS_REQ, PRODUCTOS_OPC, "ProductoID"),
}

NOMBRES = {"ventas": "Ventas", "clientes": "Clientes (maestro)", "productos": "Productos (maestro)"}
