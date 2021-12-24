$(document).ready(function() {
    $('.unhide-icon').click(function() {
        if ($(this).attr('q_id') !== undefined) {
            $.post('/unhide', {
                'q_id': $(this).attr('q_id'),
            })
        } else if ($(this).attr('a_id') !== undefined) {
            $.post('/unhide', {
                'a_id': $(this).attr('a_id')
            })
        } else if ($(this).attr('c_id') !== undefined) {
            $.post('/unhide', {
                'c_id': $(this).attr('c_id')
            })
        }

        $(this).closest('.question, .answer, .comment').hide()
    })
})