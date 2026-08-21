from django.contrib import admin
from django.urls import path

from gestion import views
from gestion.auth_views import LoginConLimiteDeIntentos

urlpatterns = [
    path('admin/', admin.site.urls),

    # Nueva ruta para la pantalla de inicio de sesión de los sindicatos
    path(
        'login/',
        LoginConLimiteDeIntentos.as_view(template_name='gestion/login.html'),
        name='login',
    ),

    path('alta/', views.registro_sindicato, name='registro_sindicato'),
    path('acuerdo-legal/', views.acuerdo_legal, name='acuerdo_legal'),
    path('subir-datos/', views.cargar_datos_sindicato, name='subir_excel'),
    path('notificaciones/', views.listar_notificaciones, name='notificaciones'),
    path('panel-imprenta/', views.panel_imprenta, name='panel_imprenta'),
]
