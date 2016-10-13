from __future__ import unicode_literals

from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template import Context
from django.template import Template
from django.utils.encoding import python_2_unicode_compatible

import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django_fsm import FSMField, transition
from django_fsm.signals import post_transition
from fir_artifacts import artifacts
from fir_artifacts.models import Artifact
from fir_plugins.models import link_to
from incidents.authorization import tree_authorization

from incidents.models import Incident, FIRModel, model_created, model_updated

ACTION_TYPES = (
    ('investigation', _('Investigation')),
    ('alerting', _('Alerting')),
    ('countermeasure', _('Countermeasure')),
    ('other', _('Other')),
)

ACTION_STATES = (
    ('created', _('Created')),
    ('assigned', _('Assigned')),
    ('blocked', _('Blocked')),
    ('closed', _('Closed'))
)

from functools import wraps


def fsm_actions(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        arg_list = list(args)
        instance = arg_list.pop(0)

        if kwargs.get('by', False):
            instance.by = kwargs['by']
        if kwargs.get('comment', False):
            instance.comment = kwargs['comment']
        if kwargs.get('business_line', False):
            instance.business_line = kwargs['business_line']

        out = func(instance, *arg_list, **kwargs)

        if kwargs.get('by', False):
            delattr(instance, 'by')
        if kwargs.get('comment', False):
            delattr(instance, 'comment')

        return out

    return wrapped


def action_permission(permission, obj_field='business_line'):
    def check_permission(instance, user):
        obj = getattr(instance, obj_field)
        return user.has_perm(permission, obj=obj)

    return check_permission


@python_2_unicode_compatible
@tree_authorization('business_line')
class Action(FIRModel, models.Model):
    opened_on = models.DateTimeField(default=datetime.datetime.now, blank=True, verbose_name=_('creation date'))
    opened_by = models.ForeignKey('auth.User', verbose_name=_('creator'))
    incident = models.ForeignKey('incidents.Incident', null=True, blank=True, related_name='actions',
                                 verbose_name=_('incident'))
    type = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name=_('type'))
    subject = models.CharField(max_length=256, verbose_name=_('subject'))
    description = models.TextField(verbose_name=_('description'))
    business_line = models.ForeignKey('incidents.BusinessLine', null=True, blank=True, related_name='actions',
                                      verbose_name=_('business line'))
    state = FSMField(default='created', choices=ACTION_STATES, protected=True, verbose_name=_('state'))
    auto_state = models.BooleanField(default=False, verbose_name=_('auto state'))

    class Meta:
        verbose_name = _('action')

    def __str__(self):
        return self.subject

    @property
    def status_id(self):
        if not self.state == 'closed':
            return 1
        return 0

    @property
    def status(self):
        if self.status_id == 1:
            return _('Active')
        return _("Inactive")

    @property
    def last_comment(self):
        return self.comments.order_by('-date')[0]

    class Meta:
        verbose_name = _('action')

    @fsm_actions
    @transition('state', source=['created', ], target='assigned',
                permission=action_permission('incidents.handle_incidents'), custom={'verbose': _('Assign')})
    def assign(self, comment=None, business_line=None, subject=None, description=None, by=None):
        """ Assign the action to a business line
        :return:
        """
        if not self.business_line:
            raise Exception
        if subject is not None:
            self.subject = subject
        if description is not None:
            self.description = description
        if self.business_line not in self.incident.concerned_business_lines.all():
            self.incident.concerned_business_lines.add(self.business_line)
            self.incident.save()

    @fsm_actions
    @transition('state', source=['assigned', ], target='blocked',
                custom={'verbose': _('Report block')}, permission=action_permission('incidents.view_incidents'))
    def block(self, comment=None, by=None):
        """ Report a block situation
        :return:
        """

    @fsm_actions
    @transition('state', source=['blocked', ], target='assigned',
                custom={'verbose': _('Unblock')}, permission=action_permission('incidents.view_incidents'))
    def unblock(self, comment=None, by=None):
        """ Report a block situation
        :return:
        """

    @fsm_actions
    @transition('state', source=['assigned', 'blocked'], target='closed',
                custom={'verbose': _('Close')}, permission=action_permission('incidents.view_incidents'))
    def close(self, comment=None, by=None):
        """ Close the action
        :return:
        """

    @fsm_actions
    @transition('state', source=['created', ], target='closed',
                custom={'verbose': _('Force close')}, permission=action_permission('incidents.handle_incidents'))
    def force_close(self, comment=None, by=None):
        """ Close forcefully the action
        :return:
        """


class ActionComment(models.Model):
    date = models.DateTimeField(default=datetime.datetime.now, blank=True)
    comment = models.TextField()
    action = models.ForeignKey(Action, related_name='comments')
    opened_by = models.ForeignKey(User)


@receiver(post_transition, sender=Action)
def action_post_transition(sender, instance, name=None, source=None, target=None, **kwargs):
    if isinstance(instance, sender):
        comment = _('%(user)s changed state to %(state)s' % {
            'user': instance.by,
            'state': instance.get_state_display()})
        if target == 'assigned':
            comment = _('%(user)s assigned this action to %(business_line)s' % {
                'user': instance.by,
                'business_line': instance.business_line})
        reason = getattr(instance, "comment", None)
        if reason and len(reason):
            comment = "%s\n\n%s" % (comment, reason)

        ActionComment.objects.create(action=instance, opened_by=instance.by,
                                     comment=comment)


@python_2_unicode_compatible
class ActionTemplate(models.Model):
    type = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name=_('type'))
    subject = models.CharField(max_length=256, verbose_name=_('subject'),
                               help_text=_('You can use Django template language here.'))
    description = models.TextField(verbose_name=_('description'),
                                   help_text=_('You can use Django template language here.'))
    business_line = models.ForeignKey('incidents.BusinessLine', null=True, blank=True, related_name='action_templates',
                                      verbose_name=_('business line'))

    def __str__(self):
        name = "[{}] {}".format(self.get_type_display(), self.subject)
        if self.business_line:
            name = "{} - {}".format(name, self.business_line)
        return name

    class Meta:
        verbose_name = _('action template')
        verbose_name_plural = _('action templates')


@python_2_unicode_compatible
class ActionList(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('name'))
    category = models.ForeignKey('incidents.IncidentCategory', null=True, blank=True, verbose_name=_('category'))
    business_lines = models.ManyToManyField('incidents.BusinessLine', blank=True, verbose_name=_('business lines'))
    detection = models.ForeignKey('incidents.Label', limit_choices_to={'group__name': 'detection'}, null=True,
                                  blank=True, verbose_name=_('detection'), related_name='+')
    plan = models.ForeignKey('incidents.Label', limit_choices_to={'group__name': 'plan'}, null=True, blank=True,
                             verbose_name=_('plan'), related_name='+')
    actions = models.ManyToManyField(ActionTemplate, verbose_name=_('actions'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('action template list')
        verbose_name_plural = _('action template list')


STATE_CHOICES = (
    ('proposed', _('Proposed')),
    ('approved', _('Approved')),
    ('refused', _('Refused')),
    ('enforced', _('Enforced')),
    ('blocked', _('Blocked')),
    ('deletion_proposed', _('Deletion proposed')),
    ('deletion_approved', _('Deletion approved')),
    ('deleted', _('Deleted'))
)


@python_2_unicode_compatible
class BlockType(models.Model):
    name = models.CharField(max_length=69, verbose_name=_("name"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('block type')
        verbose_name_plural = _('block types')


@python_2_unicode_compatible
@tree_authorization('business_line')
class BlockLocation(models.Model):
    name = models.CharField(max_length=69, verbose_name=_("name"))
    types = models.ManyToManyField(BlockType, related_name='locations', verbose_name=_('types'))
    business_line = models.ForeignKey('incidents.BusinessLine', null=True, blank=True, verbose_name=_('business line'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('block location')
        verbose_name_plural = _('block locations')


def block_permission(permission):
    def check_permission(instance, user):
        return user.has_perm(permission, obj=instance.where)

    return check_permission


@python_2_unicode_compatible
@link_to(Artifact)
class Block(FIRModel, models.Model):
    where = models.ForeignKey(BlockLocation, related_name='blocks', verbose_name=_('where'))
    how = models.ForeignKey(BlockType, related_name='blocks', verbose_name=_('how'))
    what = models.CharField(max_length=100, verbose_name=_('what'))
    state = FSMField(default='proposed', choices=STATE_CHOICES, protected=True, verbose_name=_('state'))
    comment = models.TextField(verbose_name=_('comment'), blank=True, null=True)

    incidents = models.ManyToManyField('incidents.Incident', blank=True, verbose_name=_('incidents'),
                                       related_name='blocks')

    actions = models.ManyToManyField(Action, blank=True, verbose_name=_('actions'), related_name='blocks')

    def __str__(self):
        return "{} on {}: {}".format(self.how, self.where, self.what)

    @property
    def status_id(self):
        if self.state in ['enforced', 'deletion_proposed', 'deletion_approved']:
            return 1
        return 0

    @property
    def status(self):
        if self.status_id == 1:
            return _('Active')
        return _("Inactive")

    @transition('state', source=['proposed', 'refused', 'deleted'], target='approved',
                permission=block_permission('fir_actions.can_approve_block'),
                custom={'verbose': _('Approve')})
    def approve(self, by=None):
        """ Approve this block
        :return: None
        """
        for incident in self.incidents.all():
            action = Action.objects.create(incident=incident, type='countermeasure',
                                           subject=_('Enforce block B#%(block_id)s on %(block_location)s' % {
                                               'block_id': self.id, 'block_location': self.where}, ),
                                           description=self.comment, auto_state=True,
                                           business_line=self.where.business_line, opened_by=by)
            action.assign(by=by)
            action.save()
            self.actions.add(action)

    @transition('state', source=['proposed', 'approved'], target='refused',
                permission=block_permission('fir_actions.can_approve_block'), custom={'verbose': _('Refuse')})
    def refuse(self, by=None):
        """ Refuse the block
        :return:
        """
        for action in self.actions.exclude(state='closed'):
            action.close(_('Block B#%(block_id)s refused.' % {'block_id': self.id}), by=by)
            action.save()

    @transition('state', source=['approved', 'blocked'], target='enforced',
                permission=block_permission('fir_actions.can_enforce_block'),
                custom={'verbose': _('Enforce')})
    def enforce(self, by=None):
        """ Enforce this block on the target device
        :return:
        """
        for action in self.actions.filter(state__in=['assigned', 'blocked']):
            action.close(_('Block B#%(block_id)s enforced.' % {'block_id': self.id}), by=by)
            action.save()

    @transition('state', source='approved', target='blocked',
                permission=block_permission('fir_actions.can_enforce_block'), custom={'verbose': _('Report block')})
    def block(self, comment=None, by=None):
        """ Report a problem
        :return:
        """
        for action in self.actions.filter(state='assigned'):
            action.block(comment, by=by)
            action.save()

    @transition('state', source=['blocked', ], target='approved',
                permission=block_permission('fir_actions.can_approve_block'), custom={'verbose': _('Unblock')})
    def unblock(self, comment=None, by=None):
        """ Remove problem
        :return: None
        """
        for action in self.actions.filter(state='blocked'):
            action.unblock(comment, by=by)
            action.save()

    @transition('state', source='enforced', target='deletion_proposed',
                permission=block_permission('incidents.handle_incidents'), custom={'verbose': _('Propose deletion')})
    def propose_deletion(self, by=None):
        """ Propose the deletion of the block
        :return:
        """

    @transition('state', source=['enforced', 'deletion_proposed'], target='deletion_approved',
                permission=block_permission('fir_actions.can_approve_block'), custom={'verbose': _('Approve deletion')})
    def approve_deletion(self, by=None):
        """ Approve the deletion of the block
        :return:
        """
        for incident in self.incidents.all():
            action = Action.objects.create(incident=incident, type='countermeasure',
                                           subject=_('Remove block B#%(block_id)s on %(block_location)s' % {
                                               'block_id': self.id, 'block_location': self.where}, ),
                                           description=self.comment, auto_state=True,
                                           business_line=self.where.business_line, opened_by=by)
            action.assign(by=by)
            action.save()
            self.actions.add(action)

    @transition('state', source='deletion_proposed', target='enforced',
                permission=block_permission('fir_actions.can_approve_block'), custom={'verbose': _('Refuse deletion')})
    def refuse_deletion(self, by=None):
        """ Refuse the deletion
        :return:
        """

    @transition('state', source='deletion_approved', target='deleted',
                permission=block_permission('fir_actions.can_enforce_block'), custom={'verbose': _('Delete')})
    def remove(self, by=None):
        """ Remove block from device
        :return:
        """
        for action in self.actions.exclude(state='closed'):
            action.close(_('Block B#%(block_id)s removed.' % {'block_id': self.id}), by=by)
            action.save()

    @transition('state', source='deleted', target='proposed',
                permission=block_permission('incidents.view_incidents'), custom={'verbose': _('Propose')})
    def propose(self, by=None):
        """ Propose a deleted block
        :return:
        """

    def refresh_artifacts(self):
        data = self.what
        found_artifacts = artifacts.find(data)

        artifact_list = []
        for key in found_artifacts:
            for a in found_artifacts[key]:
                artifact_list.append((key, a))

        db_artifacts = Artifact.objects.filter(value__in=[a[1] for a in artifact_list])

        exist = []

        for a in db_artifacts:
            exist.append((a.type, a.value))
            if self not in a.incidents.all():
                a.blocks.add(self)

        new_artifacts = list(set(artifact_list) - set(exist))
        all_artifacts = list(set(artifact_list))

        for a in new_artifacts:
            new = Artifact(type=a[0], value=a[1])
            new.save()
            new.blocks.add(self)

        for a in all_artifacts:
            artifacts.after_save(a[0], a[1], self)

    class Meta:
        verbose_name = _('block')
        permissions = (
            ('can_approve_block', 'Can approve block'),
            ('can_enforce_block', 'Can enforce block')
        )


def get_action_templates(category, detection, plan, bl):
    results = []

    q = Q(category=category) | Q(category__isnull=True)
    q &= Q(detection=detection) | Q(detection__isnull=True)
    q &= Q(plan=plan) | Q(plan__isnull=True)
    q &= Q(business_lines=bl) | Q(business_lines__isnull=True)
    results += ActionList.objects.filter(q)
    if not bl.is_root():
        results += get_action_templates(category, detection, plan, bl.get_parent())

    return results


@receiver(model_created, sender=Incident)
def new_event(sender, instance, **kwargs):
    context = Context({'instance': instance})
    for bl in instance.concerned_business_lines.all():
        for template in get_action_templates(instance.category, instance.detection, instance.plan, bl):
            for action in template.actions.all():
                subject = Template(action.subject).render(context)
                description = Template(action.description).render(context)
                Action.objects.create(subject=subject, description=description, type=action.type,
                                      incident=instance,
                                      business_line=bl, opened_by=instance.opened_by)


@receiver(model_created, sender=Block)
def refresh_block(sender, instance, **kwargs):
    instance.refresh_artifacts()

try:
    from fir_async.registry import async_event

    @async_event('action:created', post_save, Action, verbose_name='Action created')
    def action_created(sender, instance, **kwargs):
        if kwargs.get('created', False):
            return instance, instance.business_line, None
        return None, None


    @async_event('action:updated', model_updated, Action, verbose_name='Action updated')
    def action_created(sender, instance, **kwargs):
        return instance, instance.business_line, None
except ImportError:
    pass
