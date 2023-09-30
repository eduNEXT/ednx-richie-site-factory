"""
API routes exposed by our Custom Courses app.
"""
from django.urls import path, re_path

from rest_framework import routers

from .api import create_courses_from_request

ROUTER = routers.SimpleRouter()


urlpatterns = ROUTER.urls + [
    re_path(
        "unesco-course-sync/?$", create_courses_from_request, name="unesco_course_sync"
    ),
]
