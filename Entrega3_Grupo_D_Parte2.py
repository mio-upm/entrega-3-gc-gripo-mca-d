# -*- coding: utf-8 -*-
"""
Created on Mon Nov 25 12:23:06 2024

@author: Grupo D Métodos
"""
import pandas as pd
import pulp as lp

# Cargamos los datos
costes_df = pd.read_excel("241204_costes.xlsx")
operaciones_df = pd.read_excel("241204_datos_operaciones_programadas.xlsx")

# Limpiamos columnas y preparamos datos
costes_df.rename(columns=lambda x: x.strip(), inplace=True)
operaciones_df.rename(columns=lambda x: x.strip(), inplace=True)
costes_df.set_index("Unnamed: 0", inplace=True)

# Filtramos operaciones de los servicios relevantes
especialidades = [
    "Cardiología Pediátrica",
    "Cirugía Cardíaca Pediátrica",
    "Cirugía Cardiovascular",
    "Cirugía General y del Aparato Digestivo"
]
operaciones_filtradas = operaciones_df[operaciones_df["Especialidad quirúrgica"].isin(especialidades)]
operaciones_filtradas.loc[:, "Hora inicio"] = pd.to_datetime(operaciones_filtradas["Hora inicio"])
operaciones_filtradas.loc[:, "Hora fin"] = pd.to_datetime(operaciones_filtradas["Hora fin"])

# Creamos la matriz de incompatibilidades
operaciones = operaciones_filtradas["Código operación"].tolist()
n_operaciones = len(operaciones)
incompatibility_matrix = pd.DataFrame(0, index=operaciones, columns=operaciones)

for i in range(n_operaciones):
    for j in range(i + 1, n_operaciones):
        op1_inicio, op1_fin = operaciones_filtradas.iloc[i]["Hora inicio"], operaciones_filtradas.iloc[i]["Hora fin"]
        op2_inicio, op2_fin = operaciones_filtradas.iloc[j]["Hora inicio"], operaciones_filtradas.iloc[j]["Hora fin"]
        if op1_inicio < op2_fin and op1_fin > op2_inicio:
            incompatibility_matrix.iloc[i, j] = 1
            incompatibility_matrix.iloc[j, i] = 1

# Generamos planificaciones factibles
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

# Calculamos el coste medio de cada operación
costes_medios = costes_df.mean(axis=0).to_dict()

# Asociamos cada planificación a su coste
costes_planificaciones = {
    tuple(planificacion): sum(costes_medios[op] for op in planificacion)
    for planificacion in planificaciones
}

# Creamos el modelo de optimización
problema = lp.LpProblem(name="Cobertura_Quirofanos", sense=lp.LpMinimize)

# Variables de decisión
y = lp.LpVariable.dicts("y_k", costes_planificaciones.keys(), cat="Binary")

# Definimos la función objetivo
problema += lp.lpSum(y[k] * costes_planificaciones[k] for k in costes_planificaciones.keys()), "Coste_Total"

# Agregamos restricciones: cada operación debe estar cubierta por al menos una planificación
for operacion in operaciones:
    problema += lp.lpSum(y[k] for k in costes_planificaciones.keys() if operacion in k) >= 1, f"Cobertura_{operacion}"

# Resolvemos
problema.solve()

# Resultados
status = lp.LpStatus[problema.status]
objective_value = lp.value(problema.objective)

detalles_planificaciones = []
contador_planificacion = 1

for planificacion, valor in y.items():
    if valor.varValue > 0:  
        coste_total_planificacion = sum(costes_medios.get(operacion, 0) for operacion in planificacion)
        detalles = {
            "Planificación": f"Planificación {contador_planificacion}",
            "Operaciones": [
                {"Operación": operacion, "Coste medio": costes_medios.get(operacion, 0)}
                for operacion in planificacion
            ],
            "Coste total planificación": coste_total_planificacion
        }
        detalles_planificaciones.append(detalles)
        contador_planificacion += 1

print("=== Resultados del Modelo ===")
print(f"Estado del modelo: {status}")
print(f"Coste total mínimo: {objective_value:.2f}")
print(f"Número total de planificaciones seleccionadas / quirófanos necesarios: {len(detalles_planificaciones)}")

print("\n=== Detalle por Planificación ===")
for idx, planificacion in enumerate(detalles_planificaciones, start=1):
    print(f"\nPlanificación {idx}:")
    print("-" * 30)
    for operacion in planificacion["Operaciones"]:
        print(f"Operación: {operacion['Operación']} | Coste medio: {operacion['Coste medio']:.2f}")
    print(f"Coste total de la planificación: {planificacion['Coste total planificación']:.2f}")

# Verificación de solución
print("\n=== Verificación de la solución ===")

# 1. Verificamos cobertura
operaciones_cubiertas = set()
for planificacion in detalles_planificaciones:
    for operacion in planificacion["Operaciones"]:
        operaciones_cubiertas.add(operacion["Operación"])

if len(operaciones_cubiertas) == len(operaciones):
    print("Todas las operaciones están cubiertas.")
else:
    print(f"Faltan operaciones por cubrir: {set(operaciones) - operaciones_cubiertas}")

# 2. Verificamos incompatibilidades dentro de cada planificación
errores = 0
for idx, planificacion in enumerate(detalles_planificaciones, start=1):
    operaciones_planificacion = [op["Operación"] for op in planificacion["Operaciones"]]
    for i in range(len(operaciones_planificacion)):
        for j in range(i + 1, len(operaciones_planificacion)):
            op1, op2 = operaciones_planificacion[i], operaciones_planificacion[j]
            if incompatibility_matrix.loc[op1, op2] == 1:
                print(f"Incompatibilidad encontrada en Planificación {idx}: {op1} y {op2}")
                errores += 1

if errores == 0:
    print("No se encontraron incompatibilidades dentro de las planificaciones.")
else:
    print(f"Se encontraron {errores} incompatibilidades en las planificaciones.")


