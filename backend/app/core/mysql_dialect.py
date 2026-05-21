from __future__ import annotations

from typing import Literal

from sqlalchemy.dialects import registry
from sqlalchemy.dialects.mysql.aiomysql import MySQLDialect_aiomysql
from sqlalchemy.engine.interfaces import DBAPIConnection


class SparkitMySQLDialect_aiomysql(MySQLDialect_aiomysql):
    """AsyncAdapt_aiomysql_connection.ping() always needs reconnect; pymysql do_ping may omit it."""

    def do_ping(self, dbapi_connection: DBAPIConnection) -> Literal[True]:
        dbapi_connection.ping(False)
        return True


registry.register(
    "mysql.aiomysql",
    "app.core.mysql_dialect",
    "SparkitMySQLDialect_aiomysql",
)
