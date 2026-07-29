from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from gestion import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Nueva ruta para la pantalla de inicio de sesión de los sindicatos
    path('login/', auth_views.LoginView.as_view(template_name='gestion/login.html'), name='login'),
    
    path('acuerdo-legal/', views.acuerdo_legal, name='acuerdo_legal'),
    path('subir-datos/', views.cargar_datos_sindicato, name='subir_excel'),
]