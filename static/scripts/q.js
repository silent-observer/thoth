$(document).ready(function() {

    $('.comment-send-btn').click(function() {
        var btn = $(this)
        var text = btn.parent().find('.comment-text').val()

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
        $.post(window.location, {
            'answer': $('#send-answer-text').val()
        }, function(){
            location.reload()
        })
    });

    function updateVotes(votes, inc) {
        var current = +votes.attr('current_vote')
        var newInc = inc;
        if (current == inc) {
            newInc = 0;
        }
        
        if (votes.attr('q_id') !== null) {
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
})