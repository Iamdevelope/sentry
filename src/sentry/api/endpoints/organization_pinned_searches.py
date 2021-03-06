from __future__ import absolute_import

from rest_framework import serializers
from rest_framework.response import Response
from django.utils import six

from sentry.api.bases.organization import (
    OrganizationEndpoint,
    OrganizationPinnedSearchPermission,
)
from sentry.api.serializers import serialize
from sentry.models import SavedSearch
from sentry.models.search_common import SearchType


class OrganizationSearchSerializer(serializers.Serializer):
    type = serializers.IntegerField(required=True)
    query = serializers.CharField(required=True)

    def validate_type(self, attrs, source):
        try:
            SearchType(attrs[source])
        except ValueError as e:
            raise serializers.ValidationError(six.text_type(e))
        return attrs


class OrganizationPinnedSearchEndpoint(OrganizationEndpoint):
    permission_classes = (OrganizationPinnedSearchPermission, )

    def put(self, request, organization):
        serializer = OrganizationSearchSerializer(data=request.DATA)

        if serializer.is_valid():
            result = serializer.object
            SavedSearch.objects.create_or_update(
                organization=organization,
                owner=request.user,
                type=result['type'],
                values={'query': result['query']},
            )
            pinned_search = SavedSearch.objects.get(
                organization=organization,
                owner=request.user,
                type=result['type'],
            )
            return Response(serialize(pinned_search, request.user), status=201)
        return Response(serializer.errors, status=400)

    def delete(self, request, organization):
        try:
            search_type = SearchType(int(request.DATA.get('type', 0)))
        except ValueError as e:
            return Response(
                {'detail': 'Invalid input for `type`. Error: %s' % six.text_type(e)},
                status=400,
            )
        SavedSearch.objects.filter(
            organization=organization,
            owner=request.user,
            type=search_type.value,
        ).delete()
        return Response(status=204)
