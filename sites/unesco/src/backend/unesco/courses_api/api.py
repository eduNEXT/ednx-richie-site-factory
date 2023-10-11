"""
API endpoints for the global teacher campus sync
"""
from django.conf import settings
from django.utils.translation import get_language

from cms.api import add_plugin
from cms.models import Page
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from richie.apps.core.helpers import create_i18n_page
from richie.apps.courses.models import Course, Organization
from richie.apps.courses.utils import get_signature


def create_course(data):
    """
    Takes input data in the form of a dictionary and uses it to create a new course
    object along with its associated page, roles, and permissions. The input data must include
    'course_code', 'course_title', and 'organization_code'. If any of these fields are missing in
    the input data, a `ValidationError` is raised.

    Args:
        data (dict): A dictionary containing course creation data with keys:
            - 'course_code' (str): The code or identifier for the course.
            - 'course_title' (str): The title of the course.
            - 'organization_code' (str): The code or identifier of the organization associated with
              the course.

    Returns:
        None

    Raises:
        ValidationError: If any of the required fields are missing in the input data.

    Example:
        # Input data for course creation
        data = {
            "course_code": "CS101",
            "course_title": "Introduction to Computer Science",
            "organization_code": "ORG123"
        }

        # Create a new course based on the input data
        create_course(data)
    """
    try:
        code = data["course_code"]
        title = data["course_title"]
        organization_code = data["organization_code"]
    except KeyError:
        raise ValidationError(
            {"input_data": ["You must pass course_code, course_title and organization_code."]}
        )

    courses_page = Page.objects.get(reverse_id="courses", publisher_is_draft=True)
    org_obj = Organization.objects.get(code=organization_code.upper())
    organization_page = Page.objects.get(organization=org_obj.id, publisher_is_draft=True)

    page_obj = create_i18n_page(
        title,
        in_navigation=False,
        languages=None,
        parent=courses_page,
        reverse_id=None,
        template=Course.PAGE["template"],
    )

    course_obj = Course.objects.create(
        extended_object=page_obj, code=code
    )
    course_obj.create_page_role()

    # Add a plugin for the organization
    placeholder = course_obj.extended_object.placeholders.get(
        slot="course_organizations"
    )
    add_plugin(
        language=get_language(),
        placeholder=placeholder,
        plugin_type="OrganizationPlugin",
        **{"page": organization_page},
    )
    course_obj.create_permissions_for_organization(org_obj)


@api_view(["POST"])
def create_courses_from_request(request, version):
    """
    Create courses based on a request.

    This function takes an HTTP request, validates the authentication provided in the request header,
    exactly as the sync_course_runs_from_request in upstream richie does and attempts to create courses
    using the request data. If successful, it returns a response with a status code of 200.
    If there are validation errors or authentication issues, it returns an appropriate response with
    the corresponding status code.

    Args:
        request (HttpRequest): The HTTP request containing course creation data.
        version (str): The version of the request data. Ignored for the time being

    Returns:
        Response: A Django Response object containing the result of the course creation process.

    Raises:
        N/A

    Example:
        # Create courses from an HTTP POST request
        response = create_courses_from_request(request, "1.0")
    """
    message = request.body.decode("utf-8")

    authorization_header = request.headers.get("Authorization")
    if not authorization_header:
        return Response("Missing authentication.", status=403)


    signature_is_valid = any(
        authorization_header == get_signature(message, secret)
        for secret in getattr(settings, "RICHIE_COURSE_RUN_SYNC_SECRETS", [])
    )

    if not signature_is_valid:
        return Response("Invalid authentication.", status=401)

    result = {}
    status = 200
    try:
        create_course(request.data)
    except ValidationError as error:
        result["error"] = as_serializer_error(error)
        status = 400


    return Response(result, status=status)
