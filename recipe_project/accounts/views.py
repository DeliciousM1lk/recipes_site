from django.shortcuts import render, redirect
from django.contrib.auth import login, views as auth_views, get_user_model
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator

from .forms import CustomUserCreationForm, ProfileEditForm
from .models import CustomUser

User = get_user_model()


# ==============================================================
# 🔹 1. Регистрация и активация аккаунта
# ==============================================================

def register(request):
    """Регистрация нового пользователя с подтверждением по email."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            current_site = request.get_host()
            subject = 'Активация аккаунта на RecipeBook'

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            context = {'user': user, 'domain': current_site, 'uid': uid, 'token': token}
            email_message = render_to_string('accounts/account_activation_email.html', context)

            send_mail(
                subject, email_message, settings.DEFAULT_FROM_EMAIL, [user.email],
                html_message=email_message, fail_silently=False,
            )

            messages.info(request, 'Аккаунт успешно создан! Проверьте Email для активации.')
            return redirect('login')
        else:
            messages.error(request, 'Ошибка регистрации. Проверьте введённые данные.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def activate(request, uidb64, token):
    """Активация аккаунта по ссылке из письма."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if user.is_active:
            messages.warning(request, 'Ваш аккаунт уже активирован.')
            return redirect('login')

        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, '🎉 Аккаунт активирован! Теперь вы можете пользоваться сайтом.')
        return redirect('recipe_list')
    else:
        messages.error(request, 'Ссылка активации недействительна или просрочена.')
        return redirect('register')


@login_required
def resend_activation_email(request):
    """Повторная отправка письма активации."""
    if request.user.is_active:
        messages.warning(request, 'Ваш аккаунт уже активен.')
        return redirect('profile')

    user = request.user
    current_site = request.get_host()
    subject = 'Повторная активация аккаунта на RecipeBook'

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    context = {'user': user, 'domain': current_site, 'uid': uid, 'token': token}
    email_message = render_to_string('accounts/account_activation_email.html', context)

    send_mail(subject, email_message, settings.DEFAULT_FROM_EMAIL, [user.email],
              html_message=email_message, fail_silently=False)

    messages.success(request, f'Письмо для активации отправлено повторно на {user.email}.')
    return redirect('recipe_list')


# ==============================================================
# 🔹 2. Профиль пользователя и смена email
# ==============================================================

@login_required
def profile(request):
    """Страница профиля с формой изменения данных."""
    try:
        Recipe = request.user.recipe_set.model
        user_recipes = Recipe.objects.filter(author=request.user).order_by('-created_at')
    except AttributeError:
        user_recipes = []

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)

            if user.unconfirmed_email:
                user.save()

                new_email = user.unconfirmed_email
                current_site = request.get_host()
                subject = 'Подтверждение смены Email на RecipeBook'

                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                context = {'user': user, 'domain': current_site, 'uid': uid, 'token': token, 'new_email': new_email}
                email_message = render_to_string('accounts/email_change_email.html', context)

                send_mail(subject, email_message, settings.DEFAULT_FROM_EMAIL, [new_email],
                          html_message=email_message, fail_silently=False)

                messages.info(request, f'Письмо отправлено на {new_email} для подтверждения смены Email.')
                return redirect('profile')
            else:
                user.save()
                messages.success(request, 'Профиль успешно обновлён!')
                return redirect('profile')
        else:
            messages.error(request, 'Ошибка при обновлении профиля.')
    else:
        form = ProfileEditForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'user_recipes': user_recipes, 'profile_form': form})


def confirm_email_change(request, uidb64, token):
    """Подтверждение смены email через ссылку."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if not user or not user.unconfirmed_email:
        messages.error(request, 'Ссылка недействительна.')
        return redirect('profile')

    if default_token_generator.check_token(user, token):
        user.email = user.unconfirmed_email
        user.unconfirmed_email = None
        user.save()
        messages.success(request, f'Email успешно изменён на {user.email}.')
    else:
        messages.error(request, 'Ссылка подтверждения недействительна или просрочена.')

    return redirect('profile')


@login_required
def resend_email_change_email(request):
    """Повторная отправка письма подтверждения смены email."""
    if not request.user.unconfirmed_email:
        messages.error(request, 'Нет неподтверждённого email для смены.')
        return redirect('profile')

    user = request.user
    new_email = user.unconfirmed_email
    current_site = request.get_host()
    subject = 'Повторное подтверждение смены Email на RecipeBook'

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    context = {'user': user, 'domain': current_site, 'uid': uid, 'token': token, 'new_email': new_email}

    email_message = render_to_string('accounts/email_change_email.html', context)
    send_mail(subject, email_message, settings.DEFAULT_FROM_EMAIL, [new_email],
              html_message=email_message, fail_silently=False)

    messages.success(request, f'Письмо отправлено повторно на {new_email}.')
    return redirect('profile')


# ==============================================================
# 🔹 3. Аутентификация (вход, выход, смена пароля)
# ==============================================================

class CustomLoginView(auth_views.LoginView):
    """Авторизация пользователя."""
    template_name = 'accounts/login.html'


class CustomLogoutView(auth_views.LogoutView):
    """Выход из аккаунта."""
    next_page = '/'


class CustomPasswordChangeView(auth_views.PasswordChangeView):
    """Смена пароля через профиль."""
    template_name = 'accounts/password_change_form.html'
    success_url = reverse_lazy('profile')


# ==============================================================
# 🔹 4. Восстановление пароля
# ==============================================================

class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            messages.error(self.request, 'Аккаунт с таким Email не найден или не активирован.')
            return self.render_to_response(self.get_context_data(form=form))
        return super().form_valid(form)


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
