// some scripts

// jquery ready start
$(document).ready(function() {
	// jQuery code


    /* ///////////////////////////////////////

    THESE FOLLOWING SCRIPTS ONLY FOR BASIC USAGE,
    For sliders, interactions and other

    */ ///////////////////////////////////////


	//////////////////////// Prevent closing from click inside dropdown
    $(document).on('click', '.dropdown-menu', function (e) {
      e.stopPropagation();
    });


    $('.js-check :radio').change(function () {
        var check_attr_name = $(this).attr('name');
        if ($(this).is(':checked')) {
            $('input[name='+ check_attr_name +']').closest('.js-check').removeClass('active');
            $(this).closest('.js-check').addClass('active');
           // item.find('.radio').find('span').text('Add');

        } else {
            item.removeClass('active');
            // item.find('.radio').find('span').text('Unselect');
        }
    });


    $('.js-check :checkbox').change(function () {
        var check_attr_name = $(this).attr('name');
        if ($(this).is(':checked')) {
            $(this).closest('.js-check').addClass('active');
           // item.find('.radio').find('span').text('Add');
        } else {
            $(this).closest('.js-check').removeClass('active');
            // item.find('.radio').find('span').text('Unselect');
        }
    });



	//////////////////////// Bootstrap tooltip
	if($('[data-toggle="tooltip"]').length>0) {  // check if element exists
		$('[data-toggle="tooltip"]').tooltip()
	} // end if

	//////////////////////// Password show/hide toggle
	$('input[type="password"]').each(function() {
		var $input = $(this);
		if ($input.siblings('.password-toggle-icon').length) return;
		if ($input.closest('.password-toggle-wrapper').length) return;

		var $toggle = $('<span class="password-toggle-icon"><i class="far fa-eye"></i></span>');
		$input.after($toggle);

		var $parent = $input.parent();
		if ($parent.css('position') === 'static') {
			$parent.css('position', 'relative');
		}

		$toggle.on('click', function() {
			if ($input.attr('type') === 'password') {
				$input.attr('type', 'text');
				$toggle.html('<i class="far fa-eye-slash"></i>');
			} else {
				$input.attr('type', 'password');
				$toggle.html('<i class="far fa-eye"></i>');
			}
		});
	});





});
// jquery end

setTimeout(function(){
  $('#message').fadeOut('slow')
}, 4000)
