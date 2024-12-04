# -*- coding: utf-8 -*-
"""
Created on Mon Nov 25 12:23:06 2024

@author: Grupo D Métodos
"""

# --- MODELO RESUELTO CON DATOS DE CARDIOLOGÍA ---

import pandas as pd
import pulp as lp

# Cargamos los datos
costes_df = pd.read_excel("241204_costes.xlsx")
operaciones_df = pd.read_excel("241204_datos_operaciones_programadas.xlsx")

# Limpiamos y preparamos los datos
costes_df.rename(columns=lambda x: x.strip(), inplace=True)
operaciones_df.rename(columns=lambda x: x.strip(), inplace=True)
costes_df.set_index("Unnamed: 0", inplace=True)

# Filtramos las operaciones de Cardiología Pediátrica
operaciones_cardiologia = operaciones_df[operaciones_df["Especialidad quirúrgica"] == "Cardiología Pediátrica"]
operaciones_cardiologia["Hora inicio"] = pd.to_datetime(operaciones_cardiologia["Hora inicio"])
operaciones_cardiologia["Hora fin"] = pd.to_datetime(operaciones_cardiologia["Hora fin"])

# Creamos la matriz de incompatibilidades
operaciones = operaciones_cardiologia["Código operación"].tolist()
n_operaciones = len(operaciones)
incompatibility_matrix = pd.DataFrame(0, index=operaciones, columns=operaciones)

for i in range(n_operaciones):
    for j in range(i + 1, n_operaciones):
        op1_inicio, op1_fin = operaciones_cardiologia.iloc[i]["Hora inicio"], operaciones_cardiologia.iloc[i]["Hora fin"]
        op2_inicio, op2_fin = operaciones_cardiologia.iloc[j]["Hora inicio"], operaciones_cardiologia.iloc[j]["Hora fin"]
        if op1_inicio < op2_fin and op1_fin > op2_inicio:
            incompatibility_matrix.iloc[i, j] = 1
            incompatibility_matrix.iloc[j, i] = 1

# Construimos el modelo de optimización
problema = lp.LpProblem(name="Asignacion_Operaciones_Cardiologia", sense=lp.LpMinimize)

# Creamos las variables de decisión
quirofanos = costes_df.index.tolist()
x = lp.LpVariable.dicts("x", [(i, j) for i in operaciones for j in quirofanos], cat="Binary")

# Creamos los costes
costes = {
    (operacion, quirofano): costes_df.loc[quirofano, operacion]
    for quirofano in costes_df.index
    for operacion in costes_df.columns
    if operacion in operaciones
}

# Definimos la función objetivo
problema += lp.lpSum(x[(i, j)] * costes[(i, j)] for i in operaciones for j in quirofanos), "Coste_Total"

# Agregamos las restricciones
# 1. Cada operación debe asignarse exactamente a un quirófano
for i in operaciones:
    problema += lp.lpSum(x[(i, j)] for j in quirofanos) == 1, f"Asignacion_Unica_{i}"

# 2. Las operaciones incompatibles no pueden coincidir en el mismo quirófano
for j in quirofanos:
    for i1 in operaciones:
        for i2 in operaciones:
            if incompatibility_matrix.loc[i1, i2] == 1:
                problema += x[(i1, j)] + x[(i2, j)] <= 1, f"Incompatibilidad_{i1}_{i2}_en_{j}"

# Resolvemos el modelo
problema.solve()

# Mostramos los resultados
status = lp.LpStatus[problema.status]
objective_value = lp.value(problema.objective)
solution = {(i, j): x[(i, j)].varValue for i in operaciones for j in quirofanos if x[(i, j)].varValue > 0}

print("=== Resultados del Modelo ===")
print(f"Estado del modelo: {status}")
print(f"Coste total mínimo: {objective_value:.2f}")
print("Asignaciones óptimas:")
for (i, j), value in solution.items():
    print(f"Operación {i} asignada al quirófano {j}")
