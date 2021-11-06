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
})