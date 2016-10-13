from fir_actions.models import *
from django.contrib import admin
from django.conf import settings
from django import forms


class BlockAdminForm(forms.ModelForm):
    class Meta:
        exclude = ('artifacts', 'actions')


class BlockAdmin(admin.ModelAdmin):
    form = BlockAdminForm


admin.site.register(Action)
if settings.DEBUG:
    admin.site.register(ActionComment)
admin.site.register(ActionTemplate)
admin.site.register(ActionList)
admin.site.register(BlockLocation)
admin.site.register(BlockType)
admin.site.register(Block, BlockAdmin)

