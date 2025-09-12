# ai_services/database_service.py
import pyodbc
import pandas as pd
import logging
from typing import Dict, List, Tuple
from chat.models import DatabaseConnection, QueryHistory

logger = logging.getLogger("ai_services")


class DatabaseService:
    def __init__(self):
        self.connections = {}

    def create_connection(self, connection_config: Dict) -> str:
        """Create a database connection"""
        try:
            if connection_config["type"] == "mssql":
                conn_str = self._build_mssql_connection_string(connection_config)
                connection = pyodbc.connect(conn_str)
            else:
                raise ValueError(
                    f"Unsupported database type: {connection_config['type']}"
                )

            connection_id = (
                f"{connection_config['server']}_{connection_config['database']}"
            )
            self.connections[connection_id] = connection

            logger.info(f"Database connection created: {connection_id}")
            return connection_id

        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise

    def _build_mssql_connection_string(self, config: Dict) -> str:
        """Build MS SQL connection string"""
        driver = config.get("driver", "{ODBC Driver 17 for SQL Server}")
        server = config["server"]
        database = config["database"]
        username = config["username"]
        password = config["password"]
        port = config.get("port", 1433)

        return (
            f"DRIVER={driver};SERVER={server},{port};"
            f"DATABASE={database};UID={username};PWD={password};"
        )

    def test_connection(self, connection_config: Dict) -> Tuple[bool, str]:
        """Test database connection"""
        try:
            connection_id = self.create_connection(connection_config)
            connection = self.connections[connection_id]

            # Test with a simple query
            cursor = connection.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            cursor.close()

            if result:
                return True, "Connection successful"
            else:
                return False, "Connection test failed"

        except Exception as e:
            return False, str(e)

    def execute_query(
        self, connection_id: str, query: str, session_id: str = None
    ) -> Dict:
        """Execute SQL query and return results"""
        start_time = pd.Timestamp.now()

        try:
            if connection_id not in self.connections:
                raise ValueError(f"Connection {connection_id} not found")

            connection = self.connections[connection_id]

            # Use pandas for better data handling
            df = pd.read_sql(query, connection)

            execution_time = (pd.Timestamp.now() - start_time).total_seconds()

            # Convert DataFrame to list of dictionaries
            results = df.to_dict("records")

            # Log query execution
            if session_id:
                self._log_query_execution(
                    session_id, connection_id, query, len(results), execution_time, True
                )

            return {
                "success": True,
                "data": results,
                "columns": list(df.columns),
                "row_count": len(results),
                "execution_time": execution_time,
                "query": query,
            }

        except Exception as e:
            execution_time = (pd.Timestamp.now() - start_time).total_seconds()
            error_msg = str(e)

            # Log failed query
            if session_id:
                self._log_query_execution(
                    session_id,
                    connection_id,
                    query,
                    0,
                    execution_time,
                    False,
                    error_msg,
                )

            logger.error(f"Query execution failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "execution_time": execution_time,
                "query": query,
            }

    def get_table_schema(self, connection_id: str, table_name: str = None) -> Dict:
        """Get database schema information"""
        try:
            if connection_id not in self.connections:
                raise ValueError(f"Connection {connection_id} not found")

            connection = self.connections[connection_id]

            if table_name:
                # Get specific table schema
                query = """
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
                """
                df = pd.read_sql(query, connection, params=[table_name])

                return {
                    table_name: {
                        row["COLUMN_NAME"]: row["DATA_TYPE"] for _, row in df.iterrows()
                    }
                }
            else:
                # Get all tables and their schemas
                query = """
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS 
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """
                df = pd.read_sql(query, connection)

                schema = {}
                for _, row in df.iterrows():
                    table = row["TABLE_NAME"]
                    column = row["COLUMN_NAME"]
                    data_type = row["DATA_TYPE"]

                    if table not in schema:
                        schema[table] = {}
                    schema[table][column] = data_type

                return schema

        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            return {}

    def get_table_sample(
        self, connection_id: str, table_name: str, limit: int = 5
    ) -> List[Dict]:
        """Get sample data from a table"""
        try:
            query = f"SELECT TOP {limit} * FROM {table_name}"
            result = self.execute_query(connection_id, query)
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get table sample: {e}")
            return []

    def close_connection(self, connection_id: str):
        """Close database connection"""
        if connection_id in self.connections:
            try:
                self.connections[connection_id].close()
                del self.connections[connection_id]
                logger.info(f"Connection {connection_id} closed")
            except Exception as e:
                logger.error(f"Error closing connection {connection_id}: {e}")

    def close_all_connections(self):
        """Close all database connections"""
        for connection_id in list(self.connections.keys()):
            self.close_connection(connection_id)

    def _log_query_execution(
        self,
        session_id: str,
        connection_id: str,
        query: str,
        result_count: int,
        execution_time: float,
        success: bool,
        error_message: str = "",
    ):
        """Log query execution to database"""
        try:
            from chat.models import ChatSession

            session = ChatSession.objects.get(session_id=session_id)
            # Find the database connection - this is simplified
            # You might need to adjust based on your connection management
            db_connection = DatabaseConnection.objects.filter(
                user=session.user, is_active=True
            ).first()

            if db_connection:
                QueryHistory.objects.create(
                    session=session,
                    database_connection=db_connection,
                    query=query,
                    result_count=result_count,
                    execution_time=execution_time,
                    success=success,
                    error_message=error_message,
                )
        except Exception as e:
            logger.error(f"Failed to log query execution: {e}")

    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Basic SQL query validation"""
        # Basic security checks
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "ALTER",
            "CREATE",
            "INSERT",
            "UPDATE",
            "EXEC",
            "EXECUTE",
            "SP_",
            "XP_",
        ]

        query_upper = query.upper().strip()

        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return False, f"Query contains potentially dangerous keyword: {keyword}"

        if not query_upper.startswith("SELECT"):
            return False, "Only SELECT queries are allowed"

        return True, "Query is valid"
