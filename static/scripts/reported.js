$(document).ready(function() {
    $('.hide-icon').click(function() {
        if ($(this).attr('q_id') !== undefined) {
            $.post('/hide', {
                'q_id': $(this).attr('q_id'),
            })
        } else if ($(this).attr('a_id') !== undefined) {
            $.post('/hide', {
                'a_id': $(this).attr('a_id')
            })
        } else if ($(this).attr('c_id') !== undefined) {
            $.post('/hide', {
                'c_id': $(this).attr('c_id')
            })
        }

        $(this).closest('.question, .answer, .comment').hide()
    })
})