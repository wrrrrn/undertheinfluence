$(function() {
    externalLinks = function(doc) {
        // Add an icon to illustrate a link is an external link
        $('a', doc).filter(function() {
            var isExternal = this.hostname && this.hostname !== location.hostname;
            var hasIcon = $('.glyphicon-share', this).length;
            return isExternal && !hasIcon;
        }).append(' <span class="glyphicon glyphicon-share" aria-hidden="true"></span>');
    }

    document.body.innerHTML = document.body.innerHTML.replace(/undertheInfluence/g, "<em>underthe</em><strong>Influence</strong>");

    externalLinks(document);
});
