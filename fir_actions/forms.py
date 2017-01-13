from django import forms
from django.utils.translation import ugettext_lazy as _
from incidents.models import BusinessLine

from dal import autocomplete

from fir_actions.models import BlockLocation, Action, BlockType


class FilterBlockForm(forms.Form):
    where = forms.ModelChoiceField(queryset=BlockLocation.objects.all(), required=True)
    how = forms.ModelChoiceField(
        queryset=BlockType.objects.all(),
        label='How',
        required=False,
        widget=autocomplete.ListSelect2(forward=['where', ], url='actions:blocks_how_lookup')
    )


class MultipleBlockForm(forms.Form):
    where = forms.ModelChoiceField(queryset=BlockLocation.objects.all(), required=True)
    how = forms.ModelChoiceField(
        queryset=BlockType.objects.all(),
        label='How',
        required=True,
        widget=autocomplete.ListSelect2(forward=['where', ], url='actions:blocks_how_lookup')
    )
    what = forms.CharField(required=True, widget=forms.Textarea())
    comment = forms.CharField(required=False, widget=forms.Textarea(), help_text=_('Enter one item per line'))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(MultipleBlockForm, self).__init__(*args, **kwargs)
        self.fields['where'].queryset = BlockLocation.authorization.for_user(user, 'incidents.view_incidents')

    def clean(self):
        cleaned_data = super(MultipleBlockForm, self).clean()
        where = cleaned_data.get("where")
        how = cleaned_data.get("how")

        cleaned_data['what'] = [w for w in cleaned_data.get("what").splitlines()]

        if how not in where.types.all():
            raise forms.ValidationError(_("%(type)s is not a type of %(location)s"), code='invalid', params={
                'type': how,
                'location': where
            })
        return cleaned_data


class ActionForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        incident = kwargs.pop('incident')
        super(ActionForm, self).__init__(*args, **kwargs)
        self.fields['business_line'].queryset = BusinessLine.authorization.for_user(user, 'incidents.handle_incidents').distinct()
        self.fields['business_line'].required = True

    class Meta:
        model = Action
        exclude = ('incident', 'auto_state', 'state', 'opened_by', 'opened_on')


class ActionTransitionForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 20}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        action = kwargs.pop('action')
        super(ActionTransitionForm, self).__init__(*args, **kwargs)
        if action.state == 'created':
            self.fields['subject'] = forms.CharField(max_length=256, initial=action.subject, required=False)
            self.fields['description'] = forms.CharField(widget=forms.Textarea(attrs={'cols': 80, 'rows': 20}),
                                                         initial=action.description, required=False)
            self.fields['business_line'] = forms.ModelChoiceField(BusinessLine.authorization.for_user(user,
                                                                                                      'incidents.handle_incidents').distinct(),
                                                                  required=True, initial=action.business_line)
            self.fields['comment'].required = False
