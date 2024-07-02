from django.contrib import admin
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'author', 'publish', 'status']
    list_filter = ['status', 'created', 'publish', 'author']
    search_fields = ['title', 'body']
    prepopulated_fields = {'slug': ('title', )}  # заполнение поля slug из поля title
    raw_id_fields = ['author']  # добавлен поисковый виджет
    date_hierarchy = 'publish'  # навигационная ссылка
    ordering = ['status', 'publish']
