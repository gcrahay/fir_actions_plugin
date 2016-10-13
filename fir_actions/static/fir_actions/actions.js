

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
	$('#add-action').on('click', function(e) {
		e.preventDefault();
		ajax_action($(this), add_action);
	});
	update_async_actions();
	execute_load_async();

	$('#action_modals').on('click', '#submit-action', function(e) {
		e.preventDefault();
		submit_action();
	});
	$('#add-block').on('click', function(e) {
		e.preventDefault();
		ajax_action($(this), add_block);
	});

	$('#block_modals').on('click', '#submit-block', function(e) {
		e.preventDefault();
		submit_block();
	});
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
	$("#action_modals .modal .form-control").first().focus();
	$("#action_modals").on('click', 'button[type=submit]', function(e) {
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

function add_block(data) {
	$("#block_modals").empty();
	$("#block_modals").html(data);
	$("#addBlock").modal('show');
	$("#id_where").focus();
}

function add_action(data) {
	$("#action_modals").empty();
	$("#action_modals").html(data);
	$("#addAction").modal('show');
	$("#id_type").focus();
}

function submit_block () {
	data = $("#block_form").serialize()

	$.ajax({
		type: 'POST',
		url: $("#block_form").attr('action'),
		data: data,
		headers: {'X-CSRFToken': getCookie('csrftoken')},
		success: function (msg) {

			if (msg.status == 'success') {
                $("#addBlock").modal('hide');
				window.location = window.location;
			}

			else if (msg.status == 'error') {
				var html = $.parseHTML(msg.data);
				$("#addBlock .modal-body").html($(html).find('.modal-body'));
			}
		}
	})
}

function submit_action () {
	data = $("#action_form").serialize()

	$.ajax({
		type: 'POST',
		url: $("#action_form").attr('action'),
		data: data,
		headers: {'X-CSRFToken': getCookie('csrftoken')},
		success: function (msg) {

			if (msg.status == 'success') {
                $("#addAction").modal('hide');
				window.location = window.location;
			}

			else if (msg.status == 'error') {
				var html = $.parseHTML(msg.data);
				$("#addAction .modal-body").html($(html).find('.modal-body'));
			}
		}
	})
}