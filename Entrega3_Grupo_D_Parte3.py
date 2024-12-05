# -*- coding: utf-8 -*-
"""
Created on Tue Dec  3 15:54:47 2024

@author: Grupo D Métodos
"""
import pandas as pd
import pulp as lp

# Cargamos los datos de costes y operaciones quirúrgicas
costes_df = pd.read_excel("241204_costes.xlsx")
operaciones_df = pd.read_excel("241204_datos_operaciones_programadas.xlsx")

# Limpiamos las columnas y preparamos los datos para el modelo
costes_df.rename(columns=lambda x: x.strip(), inplace=True)
operaciones_df.rename(columns=lambda x: x.strip(), inplace=True)
costes_df.set_index("Unnamed: 0", inplace=True)

# Convertimos las columnas de horarios a formato datetime para facilitar cálculos
operaciones_df.loc[:, "Hora inicio"] = pd.to_datetime(operaciones_df["Hora inicio"])
operaciones_df.loc[:, "Hora fin"] = pd.to_datetime(operaciones_df["Hora fin"])

# Extraemos la lista de operaciones y determinamos su tamaño
operaciones = operaciones_df["Código operación"].tolist()
n_operaciones = len(operaciones)

# Creamos una matriz para identificar incompatibilidades entre operaciones
incompatibility_matrix = pd.DataFrame(0, index=operaciones, columns=operaciones)

for i in range(n_operaciones):
    for j in range(n_operaciones):
        if i != j:  # Evitamos comparar una operación consigo misma
            op1_inicio, op1_fin = operaciones_df.iloc[i]["Hora inicio"], operaciones_df.iloc[i]["Hora fin"]
            op2_inicio, op2_fin = operaciones_df.iloc[j]["Hora inicio"], operaciones_df.iloc[j]["Hora fin"]

            # Determinamos si dos operaciones tienen horarios solapados
            if not (op1_fin <= op2_inicio or op2_fin <= op1_inicio):
                incompatibility_matrix.iloc[i, j] = 1

# Definimos una función para verificar si una planificación es factible
def es_planificacion_factible(planificacion, incompatibility_matrix):
    for i in range(len(planificacion)):
        for j in range(i + 1, len(planificacion)):
            if incompatibility_matrix.loc[planificacion[i], planificacion[j]] == 1:
                return False
    return True

# Iniciamos el modelo maestro de optimización para generación de columnas
maestro = lp.LpProblem("Generación_Columnas_Quirofanos", lp.LpMinimize)

# Generamos planificaciones iniciales
planificaciones = []
for operacion in operaciones:
    asignada = False
    for planificacion in planificaciones:
        if all(incompatibility_matrix.loc[operacion, op] == 0 for op in planificacion):
            planificacion.append(operacion)
            asignada = True
            break
    if not asignada:
        planificaciones.append([operacion])

# Añadimos las variables de decisión iniciales al modelo maestro
y = lp.LpVariable.dicts("y", [tuple(plan) for plan in planificaciones], cat="Binary")
maestro += lp.lpSum(y[k] for k in y.keys()), "Minimizar_N_Quirófanos"

# Agregamos las restricciones para asegurar la cobertura de todas las operaciones
for operacion in operaciones:
    maestro += lp.lpSum(y[k] for k in y.keys() if operacion in k) >= 1, f"Cobertura_{operacion}"

# Implementamos el proceso iterativo de generación de columnas
iteracion = 0
while True:
    iteracion += 1

    # Resolvemos el modelo maestro actual
    maestro.solve()

    # Verificamos el estado del modelo
    if lp.LpStatus[maestro.status] != "Optimal":
        print("El modelo no se resolvió de manera óptima. Terminamos el proceso.")
        break

    # Calculamos los valores duales de las restricciones
    duales = {operacion: maestro.constraints[f"Cobertura_{operacion}"].pi for operacion in operaciones}

    # Generamos nuevas planificaciones candidatas
    nuevas_planificaciones = []
    for i in range(n_operaciones):
        for j in range(i + 1, n_operaciones):
            planificacion_candidata = [operaciones[i], operaciones[j]]
            if es_planificacion_factible(planificacion_candidata, incompatibility_matrix):
                coste_reducido = 1 - sum(duales.get(op, 0) for op in planificacion_candidata)
                if coste_reducido < 0:
                    nuevas_planificaciones.append(planificacion_candidata)

    # Si no hay nuevas planificaciones, terminamos el proceso
    if not nuevas_planificaciones:
        break

    # Agregamos las nuevas planificaciones al modelo maestro
    for planificacion in nuevas_planificaciones:
        nombre_variable = tuple(planificacion)
        if nombre_variable not in y:
            y[nombre_variable] = lp.LpVariable(f"y_{nombre_variable}", cat="Binary")

# Mostramos los resultados obtenidos
estado = lp.LpStatus[maestro.status]
numero_quirofanos = sum(y[k].varValue for k in y.keys() if y[k].varValue > 0)

# Creamos un reporte de las asignaciones de quirófanos
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

# Verificamos si todas las operaciones están asignadas y no hay incompatibilidades
operaciones_asignadas = set()
for resultado in resultados_quirofanos:
    operaciones_asignadas.update(resultado["Operaciones"])

faltantes = set(operaciones) - operaciones_asignadas
if not faltantes:
    print("Todas las operaciones están asignadas correctamente.")
else:
    print(f"Operaciones sin asignar: {faltantes}")
