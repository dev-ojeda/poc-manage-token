#!/usr/bin/env python3
import os
import shutil

def limpiar_pycache(base=".\\app"):
    eliminadas = []
    for root, dirs, files in os.walk(base, topdown=False):
        for d in dirs:
            if d == "__pycache__":
                ruta = os.path.join(root, d)
                shutil.rmtree(ruta)
                eliminadas.append(ruta)
    return eliminadas

if __name__ == "__main__":
    eliminadas = limpiar_pycache(".\\app")
    if eliminadas:
        print("🧹 Carpetas __pycache__ eliminadas:")
        for carpeta in eliminadas:
            print(f"   - {carpeta}")
    else:
        print("✅ No se encontraron carpetas __pycache__.")

