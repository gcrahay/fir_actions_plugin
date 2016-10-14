# -*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string
from django.http import JsonResponse, Http404
from django.utils.decorators import method_decorator
from django_fsm import has_transition_perm, can_proceed
from django.views.generic import ListView

from incidents import views as incidents_views
from incidents.authorization.decorator import authorization_required
from incidents.models import Incident
from fir_actions.forms import MultipleBlockForm, FilterBlockForm, ActionForm, ActionTransitionForm
from fir_actions.models import Block, Action, BlockLocation


@login_required
@authorization_required('incidents.handle_incidents', Incident, view_arg='event_id')
def blocks_addblock(request, event_id, authorization_target=None):
    if authorization_target is None:
        e = get_object_or_404(Incident, pk=event_id)
    else:
        e = authorization_target

    if request.method == "GET":
        block_form = MultipleBlockForm(user=request.user)
    elif request.method == "POST":
        block_form = MultipleBlockForm(request.POST, user=request.user)

        if block_form.is_valid():
            for what in block_form.cleaned_data['what']:
                blocks = Block.objects.filter(where=block_form.cleaned_data['where'],
                                              how=block_form.cleaned_data['how'], what__iexact=what)
                if blocks.count():
                    block = blocks[0]
                    if block_form.cleaned_data['comment'] != '':
                        block.comment = block_form.cleaned_data['comment']
                    if block.state == 'deleted' and can_proceed(block.propose) and \
                            has_transition_perm(block.propose, request.user):
                        block.propose()
                    block.save()
                else:
                    block = Block.objects.create(where=block_form.cleaned_data['where'],
                                                 how=block_form.cleaned_data['how'], what=what,
                                                 comment=block_form.cleaned_data['comment'])

                if e not in block.incidents.all():
                    block.incidents.add(e)
                    block.save()
                block.done_creating()
            ret = {'status': 'success'}
            return JsonResponse(ret)
        else:
            errors = render_to_string("fir_actions/blocks_form.html",
                                      {'block_form': block_form, 'event_id': event_id})
            ret = {'status': 'error', 'data': errors}
            return JsonResponse(ret)

    return render(request, "fir_actions/blocks_form.html",
                  {'block_form': block_form, 'event_id': event_id})


@login_required
def blocks_transition(request, block_id, transition_name, event_id=None):
    block = get_object_or_404(Block, pk=block_id)
    try:
        method = getattr(block, transition_name)
    except AttributeError:
        raise Http404
    try:
        if can_proceed(method) and has_transition_perm(method, request.user):
            method(by=request.user)
            block.save()
            block.done_updating()
        else:
            raise PermissionDenied
    except TypeError:
        raise Http404
    if event_id is not None:
        return redirect('incidents:details', incident_id=event_id)
    return redirect('blocks:blocks_index')


@method_decorator(login_required, name='dispatch')
class BlockList(ListView):
    template_name = 'fir_actions/blocks_index.html'
    context_object_name = 'blocks'

    def get_queryset(self):
        locations = BlockLocation.authorization.for_user(self.request.user, 'incidents.view_incidents')
        query = Q(where__in=locations)
        try:
            self.event = int(self.kwargs.get('event_id'))
            self.template_name = 'fir_actions/blocks_list.html'
            query &= Q(incidents=self.event)
            self.allow_empty = False
        except (ValueError, TypeError):
            self.event = False
        self.where = None
        self.how = None
        if self.request.method == 'POST':
            self.where = self.request.POST.get('where', None)
            self.how = self.request.POST.get('how', None)
            if self.where:
                query &= Q(where_id=self.where)
            if self.how:
                query &= Q(how_id=self.how)
            return Block.objects.filter(query)
        elif self.request.method == 'GET':
            id = self.kwargs.get('block_id', None)
            if id:
                return [get_object_or_404(Block.objects.filter(query), pk=id), ]
        return Block.objects.filter(query)

    def get_context_data(self, **kwargs):
        context = super(BlockList, self).get_context_data(**kwargs)
        context['form'] = FilterBlockForm({'where': self.where, 'how': self.how})
        context['event_id'] = self.event
        return context

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


@login_required
@authorization_required('incidents.handle_incidents', Incident, view_arg='event_id')
def actions_addaction(request, event_id, authorization_target=None):
    if authorization_target is None:
        e = get_object_or_404(Incident, pk=event_id)
    else:
        e = authorization_target

    if request.method == "POST":
        form = ActionForm(request.POST)

        if form.is_valid():
            action = form.save(commit=False)
            action.incident = e
            action.opened_by = request.user
            action.save()
            action.done_creating()
            ret = {'status': 'success'}
            return JsonResponse(ret)
        else:
            errors = render_to_string("fir_actions/actions_form.html",
                                      {'action_form': form, 'event_id': '' if event_id is None else event_id})
            ret = {'status': 'error', 'data': errors}
            return JsonResponse(ret)
    form = ActionForm()
    return render(request, "fir_actions/actions_form.html",
                  {'action_form': form, 'event_id': '' if event_id is None else event_id})


@login_required
def actions_get(request, action_id):
    action = get_object_or_404(Action, pk=action_id)
    if not request.user.has_perm('incidents.handle_incidents', obj=action.incident):
        raise PermissionDenied
    return render(request, 'fir_actions/actions_display.html', {'action': action})


@login_required
def actions_transition(request, action_id, transition_name):
    action = get_object_or_404(Action, pk=action_id)
    if request.method == "POST":
        try:
            method = getattr(action, transition_name)
        except AttributeError:
            raise Http404
        form = ActionTransitionForm(request.POST, action=action, user=request.user)

        if form.is_valid():
            try:
                if can_proceed(method) and has_transition_perm(method, request.user):
                    method(by=request.user, **form.cleaned_data)
                    action.save()
                    action.done_updating()
            except TypeError as ex:
                raise Http404
            ret = {'status': 'success'}
            return JsonResponse(ret)
        else:
            errors = render_to_string("fir_actions/actions_transition_form.html",
                                      {'transition_form': form, 'transition': transition_name, 'action': action})
            ret = {'status': 'error', 'data': errors}
            return JsonResponse(ret)
    form = ActionTransitionForm(action=action, user=request.user)
    return render(request, "fir_actions/actions_transition_form.html",
                  {'transition_form': form, 'transition': transition_name, 'action': action})


@method_decorator(login_required, name='dispatch')
class ActionList(ListView):
    template_name = 'fir_actions/actions_list.html'
    context_object_name = 'actions'
    allow_empty = False
    paginate_by = 10

    def get_queryset(self):
        queryset = Action.authorization.for_user(self.request.user, 'incidents.view_events')
        query = Q()
        try:
            self.event = int(self.kwargs.get('event_id'))
        except (ValueError, TypeError):
            self.event = False
        if self.event:
            query &= Q(incident_id=self.event)
        self.status = self.request.GET.get('status', None)
        if self.status == 'active':
            query &= Q(state__in=['created', 'assigned', 'blocked'])
        elif self.status == 'inactive':
            query &= Q(state='closed')
        return queryset.filter(query).order_by('-opened_on')

    def get_context_data(self, **kwargs):
        context = super(ActionList, self).get_context_data(**kwargs)
        context['element'] = 'main' if self.status == 'active' else 'tab'
        context['event'] = self.event
        return context

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

