from django.contrib import admin

from .models import EmailOTP, StudentProfile, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("email", "full_name", "referral_code")
    exclude = ("password",)


admin.site.register(StudentProfile)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "purpose", "created_at", "attempts", "consumed_at", "invalidated")
    exclude = ("code_hash",)
