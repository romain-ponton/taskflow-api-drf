from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tasks.views import TaskViewSet, NeedViewSet
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi



# -------------------- ROUTER DRF --------------------
router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'needs', NeedViewSet, basename='need')

# -------------------- SWAGGER / REDOC --------------------
schema_view = get_schema_view(
    openapi.Info(
        title="TaskFlow API",
        default_version='v1',
        description="Documentation des endpoints TaskFlow",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# -------------------- URLS --------------------
urlpatterns = [
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/', include(router.urls)),

    # Swagger / OpenAPI
    path('swagger<str:format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

]
