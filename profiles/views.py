from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Profile
from .serializers import ProfileSerializer, ProfileListSerializer
from .services import fetch_profile_data
from .filters import apply_filters, apply_sorting, apply_pagination
from .parser import parse_query


class ProfileListCreateView(APIView):

    def get(self, request):
        """GET /api/profiles — return all profiles with filtering, sorting, pagination"""
        queryset = Profile.objects.all()

        # Apply filters, sorting, pagination (each lives in its own file)
        queryset = apply_filters(queryset, request.query_params)
        queryset = apply_sorting(queryset, request.query_params)
        paginated, page, limit, total = apply_pagination(queryset, request.query_params)

        serializer = ProfileListSerializer(paginated, many=True)
        return Response(
            {
                "status": "success",
                "page": page,
                "limit": limit,
                "total": total,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        """POST /api/profiles — create a new profile"""
        name = request.data.get("name")

        # Validate name exists
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

        # Idempotency check — return existing profile if name already exists
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

        # Call external APIs via services.py
        api_data, error_message = fetch_profile_data(name)
        if error_message:
            return Response(
                {"status": "error", "message": error_message},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Create and save profile
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


class ProfileSearchView(APIView):

    def get(self, request):
        """GET /api/profiles/search — natural language search"""
        q = request.query_params.get("q", "").strip()

        if not q:
            return Response(
                {"status": "error", "message": "Unable to interpret query"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse plain English into filters via parser.py
        filters, error_message = parse_query(q)
        if error_message:
            return Response(
                {"status": "error", "message": error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apply parsed filters to queryset
        queryset = Profile.objects.all()
        queryset = apply_filters(queryset, filters)
        queryset = apply_sorting(queryset, request.query_params)
        paginated, page, limit, total = apply_pagination(queryset, request.query_params)

        serializer = ProfileListSerializer(paginated, many=True)
        return Response(
            {
                "status": "success",
                "page": page,
                "limit": limit,
                "total": total,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
