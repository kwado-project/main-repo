from django.contrib import admin

from .models import LearningPath, LearningPathNode, Lesson


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "estimated_minutes", "xp_reward", "order", "is_published")
    list_filter = ("is_published", "topic__subject")
    list_editable = ("is_published",)
    search_fields = ("title", "objective")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("topic",)


class NodeInline(admin.TabularInline):
    model = LearningPathNode
    extra = 0
    raw_id_fields = ("lesson", "topic")


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "examination", "is_published")
    list_filter = ("subject", "examination")
    inlines = [NodeInline]
