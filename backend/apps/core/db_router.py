class PrimaryReplicaRouter:
    """Send reads explicitly marked with `.using("replica")` to the replica.

    We do NOT route all reads to the replica automatically: money and auth
    flows must read their own writes. Read-heavy endpoints opt in via
    `apps.core.db.read_db()`.
    """

    def db_for_read(self, model, **hints):
        return "default"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == "default"
