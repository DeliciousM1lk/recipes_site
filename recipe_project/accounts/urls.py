from django.urls import path
from .views import (
    register,
    profile,
    activate,
    confirm_email_change,
    resend_activation_email,
    resend_email_change_email,
    CustomLoginView,
    CustomLogoutView,
    CustomPasswordChangeView,
    CustomPasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)

urlpatterns = [
    # 🔹 Регистрация и активация
    path('register/', register, name='register'),
    path('activate/<uidb64>/<token>/', activate, name='activate'),
    path('resend_activation_email/', resend_activation_email, name='resend_activation_email'),

    # 🔹 Аутентификация
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('password_change/', CustomPasswordChangeView.as_view(), name='password_change'),

    # 🔹 Профиль и email
    path('profile/', profile, name='profile'),
    path('confirm_email/<uidb64>/<token>/', confirm_email_change, name='confirm_email_change'),
    path('resend_email_change_email/', resend_email_change_email, name='resend_email_change_email'),

    # 🔹 Восстановление пароля
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
