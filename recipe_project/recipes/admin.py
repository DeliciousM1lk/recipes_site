from django.contrib import admin, messages
from django.utils.html import format_html
from .models import Recipe, Category, Comment


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status_colored', 'category', 'created_at', 'moderator')
    list_display_links = ('title',)
    search_fields = ('title', 'description', 'author__username', 'moderator__username')
    list_filter = ('status', 'category', 'author', 'created_at', 'moderator')

    readonly_fields = ('author', 'created_at')

    fieldsets = (
        (None, {
            'fields': ('title', 'category', 'description', 'ingredients', 'image', 'author', 'created_at'),
        }),
        ('Статус и модерация', {
            'fields': ('status', 'moderator_comment'),
            'classes': ('collapse', 'wide'),
        }),
    )

    actions = ['approve_recipes', 'reject_recipes']

    def status_colored(self, obj):
        color = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
        }.get(obj.status, 'black')
        return format_html('<b><span style="color: {};">{}</span></b>', color, obj.get_status_display())
    status_colored.short_description = 'Статус'

    def approve_recipes(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            moderator=request.user,
            moderator_comment='Одобрено модератором через массовое действие.'
        )
        self.message_user(request, f"{updated} рецептов успешно одобрено.", messages.SUCCESS)
    approve_recipes.short_description = "Одобрить выбранные рецепты"

    def reject_recipes(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            moderator=request.user,
            moderator_comment='Отклонено модератором через массовое действие.'
        )
        self.message_user(request, f"{updated} рецептов успешно отклонено.", messages.WARNING)
    reject_recipes.short_description = "Отклонить выбранные рецепты"

    def get_readonly_fields(self, request, obj=None):
        is_moderator = request.user.is_superuser or request.user.groups.filter(name='Moderators').exists()
        if not is_moderator:
            return self.readonly_fields + ('status', 'moderator_comment',)
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        is_moderator = request.user.is_superuser or request.user.groups.filter(name='Moderators').exists()
        if is_moderator and not obj.moderator:
            obj.moderator = request.user
        super().save_model(request, obj, form, change)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'short_text', 'created_at')
    search_fields = ('text', 'user__username', 'recipe__title')
    list_filter = ('created_at', 'user')

    def short_text(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    short_text.short_description = 'Комментарий'
