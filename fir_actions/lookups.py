from __future__ import unicode_literals

from django.db.models import Q
from selectable.base import ModelLookup
from selectable.registry import registry

from fir_actions.models import BlockType, BlockLocation


class BlockTypeLookup(ModelLookup):
    model = BlockType
    search_fields = ('name__icontains', )

    def get_query(self, request, term):
        location = request.GET.get('location', False)
        if not location:
            return BlockType.objects.none()
        location = request.GET.get('location', '')
        try:
            location = BlockLocation.authorization.for_user(request.user).get(id=int(location))
            query = reduce(lambda x, y: x | y, [Q(**{field: term}) for field in self.search_fields])
            return location.types.filter(query)
        except (BlockLocation.DoesNotExist, BlockLocation.MultipleObjectsReturned, ValueError):
            return BlockType.objects.none()

    def get_item_label(self, item):
        return "%s" % item.name


registry.register(BlockTypeLookup)