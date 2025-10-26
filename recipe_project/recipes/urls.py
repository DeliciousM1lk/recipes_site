from django.urls import path
from .views import home, RecipeListView, RecipeDetailView, RecipeCreateView, RecipeUpdateView, RecipeDeleteView, \
    CommentDeleteView, favorite_toggle, FavoriteListView

urlpatterns = [
    path('', home, name='home'),
    path('recipes/', RecipeListView.as_view(), name='recipe_list'),
    path('<int:pk>/', RecipeDetailView.as_view(), name='recipe_detail'),
    path('add/', RecipeCreateView.as_view(), name='recipe_add'),
    path('<int:pk>/edit/', RecipeUpdateView.as_view(), name='recipe_edit'),
    path('<int:pk>/delete/', RecipeDeleteView.as_view(), name='recipe_delete'),
    path('comment/<int:pk>/delete/', CommentDeleteView.as_view(), name='comment_delete'),
    path('<int:recipe_id>/favorite/', favorite_toggle, name='favorite_toggle'),
    path('favorites/', FavoriteListView.as_view(), name='favorite_list'),

]