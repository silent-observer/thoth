$(document).ready(function() {
    $('.hide-btn').click(function() {
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

    $('.unreport-btn').click(function() {
        if ($(this).attr('q_id') !== undefined) {
            $.post('/unreport', {
                'q_id': $(this).attr('q_id'),
            })
        } else if ($(this).attr('a_id') !== undefined) {
            $.post('/unreport', {
                'a_id': $(this).attr('a_id')
            })
        } else if ($(this).attr('c_id') !== undefined) {
            $.post('/unreport', {
                'c_id': $(this).attr('c_id')
            })
        }

        $(this).closest('.question, .answer, .comment').hide()
    })
})