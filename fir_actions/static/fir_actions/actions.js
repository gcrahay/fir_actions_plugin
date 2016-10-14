

function update_async_actions(elt) {
	if(!elt) {
		$('.action-async').on('click', function (e) {
			e.preventDefault();
			ajax_action($(this), modal_action);
		});
	} else {
		$(elt).find('.action-async').on('click', function (e) {
			e.preventDefault();
			ajax_action($(this), modal_action);
		});
	}
}


$(function() {
	update_async_actions();
	execute_load_async();
});

function ajax_action(elt, callback) {

	$.ajax({
		url: elt.data('url'),
		headers: {'X-CSRFToken': getCookie('csrftoken')},
	}).success(function(data) {
		callback(data);
	});
}

function execute_load_async () {
  $('.load-async').each( function() {
    var url = $(this).data('fetch-url');
	var widget = $(this).data('widget');
    var el = $(this);
    $.get(url).done(function (data) {
		el.html(data);
		if (widget) {
			$("#"+widget).removeClass('hidden');
		}
	});
  });
}

function modal_action(data) {
	$("#action_modals").empty();
	$("#action_modals").html(data);
	$("#action_modals .modal").modal('show');
	$("#action_modals").off('click', 'button[type=submit]');
	$("#action_modals .modal .form-control").first().focus();
	$("#action_modals").on('click', 'button[type=submit]', function(e) {
		e.stopPropagation();
		e.preventDefault();
		var form = $(this).parents('form:first');
		var data = form.serialize();
		$.ajax({
			type: 'POST',
			url: form.attr('action'),
			data: data,
			headers: {'X-CSRFToken': getCookie('csrftoken')},
			success: function (msg) {

				if (msg.status == 'success') {
					$("#action_modals .modal").modal('hide');
					$("#action_modals").empty();
					location.reload();
				}

				else if (msg.status == 'error') {
					var html = $.parseHTML(msg.data);
					$("#action_modals .modal .modal-body").html($(html).find('.modal-body'));
				}
			}
		});
	});
}
