import json
import sqlite3
from typing import Any, Optional

from icecream import ic


class Database:
    def __init__(self, db_name: str) -> None:
        """Inicializa la conexión a la base de datos"""
        self.db_name = db_name
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.connect()

    def connect(self) -> None:
        """Conecta a la base de datos"""
        try:
            self.connection = sqlite3.connect(self.db_name)
            self.cursor = self.connection.cursor()
            ic(f"Conectado a la base de datos {self.db_name}")
        except sqlite3.Error as e:
            ic(f"Error al conectar a la base de datos: {e}")
            raise

    def close(self) -> None:
        """Cierra la conexión a la base de datos"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            ic("Conexión a la base de datos cerrada")

    def execute_query(self, query: str, params: tuple = ()) -> None:
        """Ejecuta consultas de escritura (INSERT, UPDATE, DELETE)"""
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            ic("Consulta ejecutada correctamente")
        except sqlite3.Error as e:
            ic(f"Error al ejecutar la consulta: {e}")
            self.connection.rollback()
            raise

    def execute_many(self, query: str, params: list[tuple]) -> None:
        """Ejecuta múltiples consultas en batch"""
        try:
            self.cursor.executemany(query, params)
            self.connection.commit()
            ic("Consultas en batch ejecutadas correctamente")
        except sqlite3.Error as e:
            ic(f"Error en batch: {e}")
            self.connection.rollback()
            raise

    def fetch_query(self, query: str, params: tuple = ()) -> list[tuple]:
        """Consulta de lectura (retorna lista de tuplas)"""
        try:
            self.cursor.execute(query, params)
            resultados = self.cursor.fetchall()
            return resultados
        except sqlite3.Error as e:
            ic(f"Error al leer datos: {e}")
            raise

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Any]:
        """Devuelve solo un registro"""
        try:
            self.cursor.execute(query, params)
            fila = self.cursor.fetchone()
            return fila[0] if fila else None
        except sqlite3.Error as e:
            ic(f"Error en fetch_one: {e}")
            raise

    def fetch_query_json(self, query: str, params: tuple = (), output_file="resultados.json") -> bool:
        """Exporta el resultado a JSON"""
        try:
            self.cursor.execute(query, params)
            columnas = [col[0] for col in self.cursor.description]
            filas = self.cursor.fetchall()
            datos = [dict(zip(columnas, fila)) for fila in filas]
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=4, ensure_ascii=False)
            ic(f"Datos exportados a {output_file}")
            return True
        except sqlite3.Error as e:
            ic(f"Error exportando JSON: {e}")
            return False

    def fetch_query_dict(self, query: str, params: tuple = ()) -> list[dict]:
        """Retorna lista de diccionarios"""
        try:
            self.cursor.execute(query, params)
            columnas = [col[0] for col in self.cursor.description]
            filas = self.cursor.fetchall()
            return [dict(zip(columnas, fila)) for fila in filas]
        except sqlite3.Error as e:
            ic(f"Error en fetch_query_dict: {e}")
            return []