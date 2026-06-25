from ibm_dmt.modules.database_backup.connectors.base import DatabaseConnector

from ibm_dmt.modules.database_backup.connectors.mysql import MySQLConnector
from ibm_dmt.modules.database_backup.connectors.mariadb import MariaDBConnector
from ibm_dmt.modules.database_backup.connectors.postgresql import PostgreSQLConnector
from ibm_dmt.modules.database_backup.connectors.mongodb import MongoDBConnector
from ibm_dmt.modules.database_backup.connectors.redis import RedisConnector
from ibm_dmt.modules.database_backup.connectors.sqlite import SQLiteConnector
from ibm_dmt.modules.database_backup.connectors.mssql import MSSQLConnector

try:
    from ibm_dmt.modules.database_backup.connectors.oracle import OracleConnector
except ImportError:
    class OracleConnector(DatabaseConnector):
        name = "oracle"
        display_name = "Oracle Database (driver missing)"
        default_port = 1521
        def detect(self): return False
        def connect(self, *a, **kw): return False
        def list_databases(self): return []
        def dump(self, *a, **kw): raise RuntimeError("Oracle driver not installed")
        def get_server_version(self): return "N/A"
