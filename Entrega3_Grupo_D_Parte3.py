# -*- coding: utf-8 -*-
"""
Created on Tue Dec  3 15:54:47 2024

@author: User
"""
import pandas as pd
import pulp as lp

# Paso 1: Cargar los archivos Excel. Utilizamos el directorio propio para cargar los archivos.
operaciones_path = r"C:\Users\User\Desktop\Master Organización Industrial\Asiganturas 1º cuatri\Métodos Cuantitativos Avanzados\Entrega 3\241204_datos_operaciones_programadas.xlsx"
costes_path = r"C:\Users\User\Desktop\Master Organización Industrial\Asiganturas 1º cuatri\Métodos Cuantitativos Avanzados\Entrega 3\241204_costes.xlsx"
costes_df = pd.read_excel(costes_path)
operaciones_df = pd.read_excel(operaciones_path)

# Paso 2: Limpiar y preparar los datos
costes_df.rename(columns=lambda x: x.strip(), inplace=True)
operaciones_df.rename(columns=lambda x: x.strip(), inplace=True)
costes_df.set_index("Unnamed: 0", inplace=True)

# Convertir las columnas "Hora inicio" y "Hora fin" a formato datetime
operaciones_df.loc[:, "Hora inicio"] = pd.to_datetime(operaciones_df["Hora inicio"])
operaciones_df.loc[:, "Hora fin"] = pd.to_datetime(operaciones_df["Hora fin"])

# Extraer operaciones
operaciones = operaciones_df["Código operación"].tolist()  # Lista de códigos de operación
n_operaciones = len(operaciones)

# Paso 3: Generar matriz de incompatibilidades para determinar qué operaciones no pueden realizarse en el mismo quirófano debido a solapamientos en sus horarios.
incompatibility_matrix = pd.DataFrame(0, index=operaciones, columns=operaciones)

for i in range(n_operaciones):
    for j in range(n_operaciones):  # Asegurar que todas las operaciones se comparan
        if i != j:  # No es necesario comparar la misma operación
            op1_inicio, op1_fin = operaciones_df.iloc[i]["Hora inicio"], operaciones_df.iloc[i]["Hora fin"]
            op2_inicio, op2_fin = operaciones_df.iloc[j]["Hora inicio"], operaciones_df.iloc[j]["Hora fin"]
            
            # Detectar solapamiento
            if not (op1_fin <= op2_inicio or op2_fin <= op1_inicio):  # Condición correcta para solapamiento
                incompatibility_matrix.iloc[i, j] = 1


# Paso 4: Función para verificar planificaciones factible
def es_planificacion_factible(planificacion, incompatibility_matrix):
    for i in range(len(planificacion)):
        for j in range(i + 1, len(planificacion)):
            if incompatibility_matrix.loc[planificacion[i], planificacion[j]] == 1:
                return False
    return True

# Paso 5: Modelo de generación de columnas
# Crear modelo maestro inicial
maestro = lp.LpProblem("Generación_Columnas_Quirofanos", lp.LpMinimize)

# Generar planificaciones iniciales con más de una operación
planificaciones = []

for operacion in operaciones:
    asignada = False
    for planificacion in planificaciones:
        # Verificar compatibilidad con todas las operaciones en la planificación
        if all(incompatibility_matrix.loc[operacion, op] == 0 for op in planificacion):
            planificacion.append(operacion)
            asignada = True
            break
    if not asignada:
        # Crear una nueva planificación si no es compatible con ninguna existente
        planificaciones.append([operacion])

# Crear las variables de decisión con estas planificaciones iniciales
y = lp.LpVariable.dicts("y", [tuple(plan) for plan in planificaciones], cat="Binary")
maestro += lp.lpSum(y[k] for k in y.keys()), "Minimizar_N_Quirófanos"

# Restricciones iniciales: cada operación cubierta al menos una vez
for operacion in operaciones:
    maestro += lp.lpSum(y[k] for k in y.keys() if operacion in k) >= 1, f"Cobertura_{operacion}"

# Agregar restricciones con nombres únicos dentro del bucle
iteracion = 0  # Variable para identificar la iteración del bucle
while True:
    iteracion += 1

    # Resolver el modelo maestro actual
    maestro.solve()

    # Verificar el estado del modelo
    if lp.LpStatus[maestro.status] != "Optimal":
        print("El modelo no se resolvió de manera óptima. Terminando.")
        break

    # Obtener duales usando los nombres únicos de las restricciones
    duales = {}
    for operacion in operaciones:
        restriccion = maestro.constraints.get(f"Cobertura_{operacion}_Iter_{iteracion}")
        if restriccion is not None and hasattr(restriccion, "pi"):
            duales[operacion] = restriccion.pi
        else:
            duales[operacion] = 0  # Valor por defecto si no hay dual

    # Crear nuevas planificaciones candidatas
    nuevas_planificaciones = []
    for i in range(n_operaciones):
        for j in range(i + 1, n_operaciones):
            planificacion_candidata = [operaciones[i], operaciones[j]]
            if es_planificacion_factible(planificacion_candidata, incompatibility_matrix):
                coste_reducido = 1 - sum(duales.get(op, 0) for op in planificacion_candidata)
                if coste_reducido < 0:  # Nueva planificación relevante
                    nuevas_planificaciones.append(planificacion_candidata)

    # Si no hay nuevas columnas, detener
    if not nuevas_planificaciones:
        break

    # Agregar nuevas variables al modelo maestro
    for planificacion in nuevas_planificaciones:
        nombre_variable = tuple(planificacion)
        if nombre_variable not in y:
            y[nombre_variable] = lp.LpVariable(f"y_{nombre_variable}", cat="Binary")


# Paso 6: Mostrar resultados
estado = lp.LpStatus[maestro.status]
numero_quirofanos = sum(y[k].varValue for k in y.keys() if y[k].varValue > 0)

# Crear lista para mostrar asignaciones de quirófanos
resultados_quirofanos = []
quirofano_id = 1

for planificacion, var in y.items():
    if var.varValue > 0:
        detalles = {
            "Quirófano": f"Quirófano {quirofano_id}",
            "Operaciones": planificacion,
        }
        resultados_quirofanos.append(detalles)
        quirofano_id += 1

print("=== Resultados del Modelo 3 ===")
print(f"Estado del modelo: {estado}")
print(f"Número mínimo de quirófanos necesarios: {numero_quirofanos}")
print("\n=== Asignaciones de quirófanos ===")
for resultado in resultados_quirofanos:
    print(f"{resultado['Quirófano']}: {', '.join(resultado['Operaciones'])}")
    

# Obtener todas las operaciones asignadas
operaciones_asignadas = []
for resultado in resultados_quirofanos:
    operaciones_asignadas.extend(resultado["Operaciones"])

# Convertir a conjunto para eliminar duplicados
operaciones_asignadas = set(operaciones_asignadas)

# Verificar si todas las operaciones están asignadas
operaciones_totales = set(operaciones)  # Operaciones originales
operaciones_no_asignadas = operaciones_totales - operaciones_asignadas

