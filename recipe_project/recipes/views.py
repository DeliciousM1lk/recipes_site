from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Recipe, Category, Comment, Favorite
from .forms import RecipeForm, CommentForm, StepFormSet
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy, reverse
from django.http import Http404
from django.db.models import Count, Q
from django.db import transaction


def home(request):
    popular_categories = Category.objects.annotate(
        recipe_count=Count('recipe', filter=Q(recipe__status='approved'))
    ).filter(
        recipe_count__gt=0
    ).order_by('-recipe_count')[:5]

    latest_recipes = Recipe.objects.filter(status='approved').order_by('-created_at')[:6]

    return render(request, 'home.html', {
        'categories': popular_categories,
        'latest_recipes': latest_recipes,
    })


class RecipeListView(ListView):
    model = Recipe
    template_name = 'recipes/recipe_list.html'
    context_object_name = 'recipes'
    paginate_by = 9

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(status='approved')
        category_id = self.request.GET.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
        search_query = self.request.GET.get('q')
        if search_query:
            qs = qs.filter(title__icontains=search_query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class RecipeDetailView(DetailView):
    model = Recipe
    template_name = 'recipes/recipe_detail.html'
    context_object_name = 'recipe'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            is_moderator = user.is_superuser or user.groups.filter(name='Moderators').exists()
            return qs.filter(
                Q(status='approved') |
                Q(author=user) |
                (Q(status__in=['draft', 'pending', 'rejected']) & Q(author=user)) |
                (Q(status__in=['pending', 'rejected']) & Q(moderator=user))
            ).distinct()
        return qs.filter(status='approved')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recipe = self.get_object()
        user = self.request.user
        if 'comment_form' not in kwargs:
            context['comment_form'] = CommentForm()
        context['is_favorite'] = False
        if user.is_authenticated:
            context['is_favorite'] = Favorite.objects.filter(user=user, recipe=recipe).exists()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status != 'approved':
            raise Http404("Этот рецепт еще не одобрен для комментариев.")
        if not request.user.is_authenticated:
            return redirect(f'{reverse("login")}?next={request.path}')
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.recipe = self.object
            comment.save()
            return redirect('recipe_detail', pk=self.object.pk)
        context = self.get_context_data(comment_form=form)
        return self.render_to_response(context)


@method_decorator(login_required, name='dispatch')
class RecipeCreateView(CreateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'recipes/recipe_form.html'
    success_url = reverse_lazy('recipe_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['step_formset'] = StepFormSet(self.request.POST, self.request.FILES)
        else:
            data['step_formset'] = StepFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        step_formset = context['step_formset']
        with transaction.atomic():
            form.instance.author = self.request.user
            form.instance.status = 'pending'
            self.object = form.save()
            messages.info(self.request, "Ваш рецепт отправлен на проверку. Вы увидите его после одобрения модератором.")
            if step_formset.is_valid():
                step_formset.instance = self.object
                steps = step_formset.save(commit=False)
                for i, step in enumerate(steps):
                    if not step.pk or step.pk and step_formset.forms[i] not in step_formset.deleted_forms:
                        step.step_number = i + 1
                        step.save()
                for step_form in step_formset.deleted_forms:
                    if step_form.instance.pk:
                        step_form.instance.delete()
                return redirect(self.get_success_url())
            else:
                return self.form_invalid(form)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(login_required, name='dispatch')
class RecipeUpdateView(UpdateView):
    model = Recipe
    form_class = RecipeForm
    template_name = 'recipes/recipe_form.html'
    success_url = reverse_lazy('recipe_list')

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(author=self.request.user)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['step_formset'] = StepFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            data['step_formset'] = StepFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        form.instance.status = 'pending'
        form.instance.moderator = None
        form.instance.moderator_comment = ''
        messages.info(self.request, "Рецепт отправлен на модерацию после редактирования.")
        context = self.get_context_data()
        step_formset = context['step_formset']
        with transaction.atomic():
            self.object = form.save()
            if step_formset.is_valid():
                step_formset.instance = self.object
                steps = step_formset.save(commit=False)
                for i, step in enumerate(steps):
                    if not step.pk or step.pk and step_formset.forms[i] not in step_formset.deleted_forms:
                        step.step_number = i + 1
                        step.save()
                for step_form in step_formset.deleted_forms:
                    if step_form.instance.pk:
                        step_form.instance.delete()
                return redirect(self.get_success_url())
            else:
                return self.form_invalid(form)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(login_required, name='dispatch')
class RecipeDeleteView(DeleteView):
    model = Recipe
    template_name = 'recipes/recipe_confirm_delete.html'
    success_url = reverse_lazy('recipe_list')

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(author=self.request.user)


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'recipes/comment_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('recipe_detail', kwargs={'pk': self.object.recipe.pk})

    def test_func(self):
        comment = self.get_object()
        return comment.user == self.request.user or self.request.user.is_staff


@login_required
def favorite_toggle(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    if recipe.status != 'approved':
        messages.error(request, "Нельзя добавить в избранное неодобренный рецепт.")
        return redirect('recipe_detail', pk=recipe_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)
    if not created:
        favorite.delete()
        messages.success(request, f'Рецепт {recipe.title} удален из избранного.')
    else:
        messages.success(request, f'Рецепт {recipe.title} добавлен в избранное.')
    return redirect('recipe_detail', pk=recipe_id)


class FavoriteListView(LoginRequiredMixin, ListView):
    model = Favorite
    template_name = 'recipes/favorite_list.html'
    context_object_name = 'favorites'
    paginate_by = 9

    def get_queryset(self):
        user = self.request.user
        queryset = Favorite.objects.filter(user=user).select_related('recipe', 'recipe__category')
        queryset = queryset.filter(recipe__status='approved')
        search_query = self.request.GET.get('q')
        category_id = self.request.GET.get('category')
        if search_query:
            queryset = queryset.filter(recipe__title__icontains=search_query)
        if category_id:
            queryset = queryset.filter(recipe__category_id=category_id)
        return queryset.order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('q', '')
        return context
