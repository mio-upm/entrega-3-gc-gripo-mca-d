# -*- coding: utf-8 -*-
"""
Created on Mon Nov 25 12:23:06 2024

@author: Grupo D Métodos
"""

import pandas as pd
import pulp as lp

# Paso 1: Cargar los archivos Excel
archivo_costes = "C:/Users/inigo/OneDrive/Escritorio/UNIVERSIDAD/MÁSTER/4. Métodos Cuantitavos/Entrega 3/241204_costes.xlsx"
archivo_operaciones = "C:/Users/inigo/OneDrive/Escritorio/UNIVERSIDAD/MÁSTER/4. Métodos Cuantitavos/Entrega 3/241204_datos_operaciones_programadas.xlsx"

# 1.1 Leemos los datos de los 2 excel
costes_df = pd.read_excel(archivo_costes)
operaciones_df = pd.read_excel(archivo_operaciones)

# 1.2 Limpiamos las columnas por si existen espacios que pueden dar error luego
costes_df.rename(columns=lambda x: x.strip(), inplace=True)
operaciones_df.rename(columns=lambda x: x.strip(), inplace=True)

# Paso 2: Matriz de incompatibiilidades (Li)
# 2.1 Cambiamos el formato a datetime
operaciones_df["Hora inicio"] = pd.to_datetime(operaciones_df["Hora inicio"])
operaciones_df["Hora fin"] = pd.to_datetime(operaciones_df["Hora fin"])

# 2.2 Obtenemos la lista de operaciones y su cantidad
operaciones = operaciones_df["Código operación"].tolist()
n_operaciones = len(operaciones)

# 2.3 Inicializamos una matriz de ceros (n x n)
incompatibility_matrix = pd.DataFrame(0, index=operaciones, columns=operaciones)

# 2.4 Llenamos la matriz de incompatibilidades: 1 si dos operaciones son incompatibles
for i in range(n_operaciones):
    for j in range(i + 1, n_operaciones):  # Comparar solo pares una vez
        # Extraer horarios de las operaciones
        op1_inicio, op1_fin = operaciones_df.iloc[i]["Hora inicio"], operaciones_df.iloc[i]["Hora fin"]
        op2_inicio, op2_fin = operaciones_df.iloc[j]["Hora inicio"], operaciones_df.iloc[j]["Hora fin"]
        
        # Detectar solapamiento de horarios
        if op1_inicio < op2_fin and op1_fin > op2_inicio:
            incompatibility_matrix.iloc[i, j] = 1
            incompatibility_matrix.iloc[j, i] = 1

# Mostrar la matriz de incompatibilidades
print("Matriz de incompatibilidades:")
print(incompatibility_matrix.head())
