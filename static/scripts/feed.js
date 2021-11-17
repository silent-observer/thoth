$(document).ready(function() {
    function updateVotes(votes, inc) {
        if (votes.attr('logged_in') === 'False') return
        var current = +votes.attr('current_vote')
        var newInc = inc;
        if (current == inc) {
            newInc = 0;
        }
        
        $.post('/votes', {
            'q_id': votes.attr('q_id'),
            'vote': newInc
        })
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