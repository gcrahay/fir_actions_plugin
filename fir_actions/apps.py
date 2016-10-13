from django.apps import AppConfig


class ActionsConfig(AppConfig):
    name = 'fir_actions'
    verbose_name = 'Actions'

    def ready(self):
        from fir_plugins.links import registry
        registry.register_reverse_link("(?:^|\s)B\#(\d+)", 'actions:blocks_details', model='fir_actions.Block', reverse="B#{}")
