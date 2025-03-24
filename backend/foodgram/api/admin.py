from django.contrib import admin
from .models import Tag, Ingredient, Recipe, RecipeIngredient

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'total_favorites')
    search_fields = ('author__username', 'name')
    list_filter = ('tags',)
    inlines = [RecipeIngredientInline]
    readonly_fields = ('total_favorites',)

    def total_favorites(self, obj):
        return obj.favorites.count()
    total_favorites.short_description = 'Total Favorites'
