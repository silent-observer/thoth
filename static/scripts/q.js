$(document).ready(function() {

    $('.comment-send-btn').click(function() {
        var btn = $(this)
        var text = btn.parent().find('.comment-text').val()

        $('.error').remove()
        if (text.length < 10 || text.length > 280) {
            var comments = btn.parent().find('.comments')
            var errorText = $($.parseHTML('<p class="error">Комментарий должен содержать от 10 до 280 символов</p>'))
            comments.append(errorText)
            return
        }

        if (btn.attr('q_id') !== null) {
            $.post(window.location, {
                'q_id': btn.attr('q_id'),
                'comment':text
            })
        } else {
            $.post(window.location, {
                'a_id': btn.attr('a_id'),
                'comment': text
            })
        }

        var comments = btn.parent().find('.comments')
        var newComment = $($.parseHTML('<div class="comment"></div>'))
        newComment.append(btn.parent().find('.comment-send-form .profile-picture'))
        var commentText = $($.parseHTML('<div class="comment-body"><p>' + text + '</p></div>'))
        newComment.append(btn.parent().find('.comment-send-form .profile-picture'))
        newComment.append(commentText)
        comments.append(newComment)
    });

    $('#answer-send-btn').click(function() {
        var text = $('#send-answer-text').val()

        $('.error').remove()
        if (text.length < 10 || text.length > 2000) {
            var sect = $(this).parent()
            var errorText = $($.parseHTML('<p class="error">Ответ должен содержать от 10 до 2000 символов</p>'))
            sect.prepend(errorText)
            return
        }

        $.post(window.location, {
            'answer': text
        }, function(){
            location.reload()
        })
    });

    function updateVotes(votes, inc) {
        if (votes.attr('logged_in') === 'False') return
        var current = +votes.attr('current_vote')
        var newInc = inc;
        if (current == inc) {
            newInc = 0;
        }
        
        if (votes.attr('q_id') !== undefined) {
            $.post('/votes', {
                'q_id': votes.attr('q_id'),
                'vote': newInc
            })
        } else {
            $.post('/votes', {
                'a_id': votes.attr('a_id'),
                'vote': newInc
            })
        }
        let v = votes.find('.vote-text').text()
        votes.find('.vote-text').text(+v - current + newInc)

        votes.find('.vote-up, .vote-down').removeClass('vote-selected')
        if (newInc === 1)
            votes.find('.vote-up').addClass('vote-selected')
        if (newInc === -1)
            votes.find('.vote-down').addClass('vote-selected')
        votes.attr('current_vote', newInc)
    }

    $('.vote-up').click(function() {
        updateVotes($(this).parent(), 1)
    });

    $('.vote-down').click(function() {
        updateVotes($(this).parent(), -1)
    });

    $('.report-icon').click(function() {
        if ($(this).attr('q_id') !== undefined) {
            $.post('/report', {
                'q_id': $(this).attr('q_id'),
            })
        } else if ($(this).attr('a_id') !== undefined) {
            $.post('/report', {
                'a_id': $(this).attr('a_id')
            })
        } else if ($(this).attr('c_id') !== undefined) {
            $.post('/report', {
                'c_id': $(this).attr('c_id')
            })
        }
    })

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