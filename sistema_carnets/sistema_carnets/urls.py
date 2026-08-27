from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView

from gestion import views
from gestion.auth_views import LoginConLimiteDeIntentos, RecuperarPasswordConLimite

urlpatterns = [
    path('admin/', admin.site.urls),

    # Portada pública. Sin vista propia: no tiene lógica, solo enseña los dos
    # caminos de entrada. La raíz devolvía 404 y quien escribía la dirección a
    # secas —que es lo que hace la gente— se encontraba un error sin ninguna
    # indicación de adónde ir.
    path(
        '',
        TemplateView.as_view(template_name='gestion/portada.html'),
        name='portada',
    ),

    # Página de ayuda. Pública a propósito: quien más la necesita es justo
    # quien no consigue entrar. Antes el botón de la portada era un mailto:,
    # que en un ordenador de local sindical sin cliente de correo configurado
    # no abre nada.
    path(
        'ayuda/',
        TemplateView.as_view(template_name='gestion/ayuda.html'),
        name='ayuda',
    ),

    # Nueva ruta para la pantalla de inicio de sesión de los sindicatos
    path(
        'login/',
        LoginConLimiteDeIntentos.as_view(template_name='gestion/login.html'),
        name='login',
    ),

    # Cierre de sesión. Solo por POST (lo impone LogoutView desde Django 5):
    # con GET bastaba una <img src="/salir/"> en cualquier página ajena para
    # echar al sindicato de la suya. Vuelve a la portada, no al login, para no
    # invitar a volver a entrar en un equipo compartido.
    path(
        'salir/',
        auth_views.LogoutView.as_view(next_page='portada'),
        name='logout',
    ),

    # Reposición de contraseña. La ruta conserva el nombre que ya tenía el
    # despliegue beta ('/recuperar-password/') para no romper los enlaces que
    # los sindicatos puedan tener guardados.
    path(
        'recuperar-password/',
        RecuperarPasswordConLimite.as_view(
            template_name='gestion/password/solicitar.html',
            email_template_name='gestion/password/correo.txt',
            subject_template_name='gestion/password/asunto.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'recuperar-password/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='gestion/password/enviado.html',
        ),
        name='password_reset_done',
    ),
    path(
        'recuperar-password/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='gestion/password/nueva.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'recuperar-password/hecho/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='gestion/password/hecho.html',
        ),
        name='password_reset_complete',
    ),

    path('alta/', views.registro_sindicato, name='registro_sindicato'),
    path('acuerdo-legal/', views.acuerdo_legal, name='acuerdo_legal'),
    path('subir-datos/', views.cargar_datos_sindicato, name='subir_excel'),
    path('notificaciones/', views.listar_notificaciones, name='notificaciones'),
    path('panel-imprenta/', views.panel_imprenta, name='panel_imprenta'),
]
