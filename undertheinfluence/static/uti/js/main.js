$(function() {
    externalLinks = function(el) {
        // Add an icon to illustrate a link is an external link
        $('a', el).filter(function() {
            var isExternal = this.hostname && this.hostname !== location.hostname;
            var hasIcon = $('.glyphicon-share', this).length;
            return isExternal && !hasIcon;
        }).append(' <span class="glyphicon glyphicon-share" aria-hidden="true"></span>');
    }
    externalLinks(document);
});
