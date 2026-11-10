from django.contrib import admin


class ReadOnlyAdmin(admin.ModelAdmin):
    """For ledgers and records that must only change through application logic."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
