class LigRouter:
    """Routes every apps.sync model to the `lig` database alias (the
    merchant's own store, LiG). Everything else keeps using the default
    PricePilot database.

    The `lig` alias only exists when LIG_DATABASE_URL is configured, and the
    sync services guard against running when it isn't — so this router is
    safe to install unconditionally.
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "sync":
            return "lig"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "sync":
            return "lig"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == "sync" or obj2._meta.app_label == "sync":
            return obj1._meta.app_label == "sync" and obj2._meta.app_label == "sync"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "sync":
            # Unmanaged models — never create/migrate these tables anywhere.
            return False
        return None
