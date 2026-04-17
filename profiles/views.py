import httpx
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Profile
from .serializers import ProfileSerializer, ProfileListSerializer


def get_age_group(age):
    """Classify age into a group based on task rules"""
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"


def call_external_apis(name):
    """
    Call all three external APIs concurrently and return processed data.
    Returns (data_dict, error_response) — one will always be None.
    """
    import asyncio

    async def fetch_all():
        async with httpx.AsyncClient(timeout=10.0) as client:
            gender_task = client.get(f"https://api.genderize.io?name={name}")
            age_task = client.get(f"https://api.agify.io?name={name}")
            nation_task = client.get(f"https://api.nationalize.io?name={name}")

            gender_res, age_res, nation_res = await asyncio.gather(
                gender_task, age_task, nation_task
            )
            return gender_res.json(), age_res.json(), nation_res.json()

    gender_data, age_data, nation_data = asyncio.run(fetch_all())

    # Validate Genderize response
    if not gender_data.get("gender") or gender_data.get("count", 0) == 0:
        return None, Response(
            {"status": "error", "message": "Genderize returned an invalid response"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Validate Agify response
    if age_data.get("age") is None:
        return None, Response(
            {"status": "error", "message": "Agify returned an invalid response"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Validate Nationalize response
    countries = nation_data.get("country", [])
    if not countries:
        return None, Response(
            {"status": "error", "message": "Nationalize returned an invalid response"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Pick country with highest probability
    top_country = max(countries, key=lambda c: c["probability"])

    return {
        "gender": gender_data["gender"],
        "gender_probability": gender_data["probability"],
        "sample_size": gender_data["count"],
        "age": age_data["age"],
        "age_group": get_age_group(age_data["age"]),
        "country_id": top_country["country_id"],
        "country_probability": top_country["probability"],
    }, None


class ProfileListCreateView(APIView):

    def get(self, request):
        """GET /api/profiles — return all profiles with optional filters"""
        queryset = Profile.objects.all()

        # Apply filters — case insensitive
        gender = request.query_params.get("gender")
        country_id = request.query_params.get("country_id")
        age_group = request.query_params.get("age_group")

        if gender:
            queryset = queryset.filter(gender__iexact=gender)
        if country_id:
            queryset = queryset.filter(country_id__iexact=country_id)
        if age_group:
            queryset = queryset.filter(age_group__iexact=age_group)

        serializer = ProfileListSerializer(queryset, many=True)
        return Response(
            {
                "status": "success",
                "count": queryset.count(),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """POST /api/profiles — create a new profile"""

        # Validate name field exists
        name = request.data.get("name")
        if name is None or name == "":
            return Response(
                {"status": "error", "message": "name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate name is a string
        if not isinstance(name, str):
            return Response(
                {"status": "error", "message": "name must be a string"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        name = name.strip().lower()

        # Check for existing profile — idempotency
        existing = Profile.objects.filter(name=name).first()
        if existing:
            serializer = ProfileSerializer(existing)
            return Response(
                {
                    "status": "success",
                    "message": "Profile already exists",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        # Call external APIs
        api_data, error = call_external_apis(name)
        if error:
            return error

        # Create and save the profile
        profile = Profile.objects.create(name=name, **api_data)

        serializer = ProfileSerializer(profile)
        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileDetailView(APIView):

    def get(self, request, pk):
        """GET /api/profiles/{id} — return a single profile"""
        try:
            profile = Profile.objects.get(pk=pk)
        except Profile.DoesNotExist:
            return Response(
                {"status": "error", "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProfileSerializer(profile)
        return Response(
            {
                "status": "success",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        """DELETE /api/profiles/{id} — delete a profile"""
        try:
            profile = Profile.objects.get(pk=pk)
        except Profile.DoesNotExist:
            return Response(
                {"status": "error", "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
