$(function() {
    externalLinks = function() {
        // Add an icon to illustrate a link is an external link
        $('a').filter(function() {
            return this.hostname && this.hostname !== location.hostname;
        }).append(' <span class="glyphicon glyphicon-share" aria-hidden="true"></span>');
    }
    externalLinks();
});
