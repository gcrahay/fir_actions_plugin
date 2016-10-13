from django.conf.urls import url
from fir_actions import views

urlpatterns = [
    url(r'^$', views.ActionList.as_view(), name='actions_dashboard'),
    url(r'^(?P<action_id>\d+)/display$', views.actions_get, name='actions_display'),
    url(r'^(?P<event_id>\d+)$', views.ActionList.as_view(), name='actions_list'),
    url(r'^(?P<event_id>\d+)/add$', views.actions_addaction, name='actions_add'),
    url(r'^transition/(?P<action_id>\d+)/(?P<transition_name>[a-z_]+)$', views.actions_transition, name='actions_transition'),
    url(r'^blocks$', views.BlockList.as_view(), name='blocks_index'),
    url(r'^blocks/(?P<block_id>\d+)$', views.BlockList.as_view(), name='blocks_details'),
    url(r'^blocks/(?P<event_id>\d+)/list', views.BlockList.as_view(), name='blocks_list'),
    url(r'^blocks/(?P<event_id>\d+)/add$', views.blocks_addblock, name='blocks_add'),
    url(r'^blocks/transition/(?P<block_id>\d+)/(?P<transition_name>[a-z_]+)(?:/(?P<event_id>\d+))?$', views.blocks_transition, name='blocks_transition'),
]
