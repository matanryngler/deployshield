"""Tests for psql, mysql, mongosh, redis-cli, and SQL checker."""

from __future__ import annotations


class TestSQLChecker:
    def test_select_safe(self, v):
        assert v._check_sql_safe("SELECT * FROM users") is True

    def test_show_safe(self, v):
        assert v._check_sql_safe("SHOW TABLES") is True

    def test_describe_safe(self, v):
        assert v._check_sql_safe("DESCRIBE users") is True

    def test_explain_safe(self, v):
        assert v._check_sql_safe("EXPLAIN SELECT * FROM users") is True

    def test_drop_blocked(self, v):
        assert v._check_sql_safe("DROP TABLE users") is False

    def test_delete_blocked(self, v):
        assert v._check_sql_safe("DELETE FROM users") is False

    def test_truncate_blocked(self, v):
        assert v._check_sql_safe("TRUNCATE TABLE users") is False

    def test_insert_blocked(self, v):
        assert v._check_sql_safe("INSERT INTO users VALUES (1)") is False

    def test_update_blocked(self, v):
        assert v._check_sql_safe("UPDATE users SET name='x'") is False

    def test_create_blocked(self, v):
        assert v._check_sql_safe("CREATE TABLE foo (id INT)") is False

    def test_empty_safe(self, v):
        assert v._check_sql_safe("") is True

    def test_psql_backslash_dt_safe(self, v):
        assert v._check_sql_safe("\\dt") is True

    def test_psql_backslash_l_safe(self, v):
        assert v._check_sql_safe("\\l") is True

    def test_psql_backslash_shell_blocked(self, v):
        assert v._check_sql_safe("\\! rm -rf /") is False

    def test_psql_backslash_copy_blocked(self, v):
        assert v._check_sql_safe("\\copy users to '/tmp/out'") is False

    def test_unknown_sql_default_deny(self, v):
        assert v._check_sql_safe("VACUUM") is False

    def test_case_insensitive(self, v):
        assert v._check_sql_safe("select * from users") is True
        assert v._check_sql_safe("DROP table users") is False


class TestPsql:
    def test_empty_args_safe(self, v):
        assert v.check_psql([]) is True

    def test_help_safe(self, v):
        assert v.check_psql(["--help"]) is True

    def test_version_safe(self, v):
        assert v.check_psql(["--version"]) is True

    def test_list_databases_safe(self, v):
        assert v.check_psql(["-l"]) is True

    def test_list_databases_long_safe(self, v):
        assert v.check_psql(["--list"]) is True

    def test_select_safe(self, v):
        assert v.check_psql(["-c", "SELECT * FROM users"]) is True

    def test_drop_blocked(self, v):
        assert v.check_psql(["-c", "DROP TABLE users"]) is False

    def test_compact_c_flag_safe(self, v):
        assert v.check_psql(["-cSELECT 1"]) is True

    def test_compact_c_flag_blocked(self, v):
        assert v.check_psql(["-cDROP TABLE users"]) is False

    def test_file_blocked(self, v):
        assert v.check_psql(["-f", "script.sql"]) is False

    def test_file_long_blocked(self, v):
        assert v.check_psql(["--file", "script.sql"]) is False

    def test_connection_only_safe(self, v):
        """Connecting to a database without -c or -f is allowed."""
        assert v.check_psql(["-h", "localhost", "-U", "user", "mydb"]) is True


class TestMySQL:
    def test_empty_args_safe(self, v):
        assert v.check_mysql([]) is True

    def test_help_safe(self, v):
        assert v.check_mysql(["--help"]) is True

    def test_select_safe(self, v):
        assert v.check_mysql(["-e", "SELECT * FROM users"]) is True

    def test_drop_blocked(self, v):
        assert v.check_mysql(["-e", "DROP TABLE users"]) is False

    def test_execute_long_flag(self, v):
        assert v.check_mysql(["--execute", "SELECT 1"]) is True

    def test_execute_long_flag_blocked(self, v):
        assert v.check_mysql(["--execute", "DELETE FROM users"]) is False

    def test_compact_e_flag_safe(self, v):
        assert v.check_mysql(["-eSELECT 1"]) is True

    def test_compact_e_flag_blocked(self, v):
        assert v.check_mysql(["-eDROP TABLE users"]) is False

    def test_init_command_blocked(self, v):
        assert v.check_mysql(["--init-command", "DELETE FROM users"]) is False

    def test_init_command_equals_blocked(self, v):
        assert v.check_mysql(["--init-command=DELETE FROM users"]) is False


class TestMongosh:
    def test_empty_args_safe(self, v):
        assert v.check_mongosh([]) is True

    def test_help_safe(self, v):
        assert v.check_mongosh(["--help"]) is True

    def test_version_safe(self, v):
        assert v.check_mongosh(["--version"]) is True

    def test_eval_find_safe(self, v):
        assert v.check_mongosh(["--eval", "db.users.find()"]) is True

    def test_eval_count_safe(self, v):
        assert v.check_mongosh(["--eval", "db.users.count()"]) is True

    def test_eval_drop_blocked(self, v):
        assert v.check_mongosh(["--eval", "db.users.drop()"]) is False

    def test_eval_deleteMany_blocked(self, v):
        assert v.check_mongosh(["--eval", "db.users.deleteMany({})"]) is False

    def test_eval_insert_blocked(self, v):
        assert v.check_mongosh(["--eval", "db.users.insertOne({name:'x'})"]) is False

    def test_eval_unknown_js_blocked(self, v):
        assert v.check_mongosh(["--eval", "db.runCommand({foo:1})"]) is False

    def test_file_blocked(self, v):
        assert v.check_mongosh(["--file", "script.js"]) is False

    def test_f_flag_blocked(self, v):
        assert v.check_mongosh(["-f", "script.js"]) is False


class TestRedisCli:
    def test_empty_args_safe(self, v):
        assert v.check_redis_cli([]) is True

    def test_help_safe(self, v):
        assert v.check_redis_cli(["--help"]) is True

    def test_get_safe(self, v):
        assert v.check_redis_cli(["GET", "mykey"]) is True

    def test_keys_safe(self, v):
        assert v.check_redis_cli(["KEYS", "*"]) is True

    def test_info_safe(self, v):
        assert v.check_redis_cli(["INFO"]) is True

    def test_ping_safe(self, v):
        assert v.check_redis_cli(["PING"]) is True

    def test_set_blocked(self, v):
        assert v.check_redis_cli(["SET", "mykey", "value"]) is False

    def test_del_blocked(self, v):
        assert v.check_redis_cli(["DEL", "mykey"]) is False

    def test_flushall_blocked(self, v):
        assert v.check_redis_cli(["FLUSHALL"]) is False

    def test_flushdb_blocked(self, v):
        assert v.check_redis_cli(["FLUSHDB"]) is False

    def test_config_get_safe(self, v):
        assert v.check_redis_cli(["CONFIG", "GET", "maxmemory"]) is True

    def test_config_set_blocked(self, v):
        assert v.check_redis_cli(["CONFIG", "SET", "maxmemory", "100mb"]) is False

    def test_host_flag_skipped(self, v):
        assert (
            v.check_redis_cli(["-h", "localhost", "-p", "6379", "GET", "mykey"]) is True
        )

    def test_scan_safe(self, v):
        assert v.check_redis_cli(["SCAN", "0"]) is True
