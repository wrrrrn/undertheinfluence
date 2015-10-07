$(function() {
    commify = function(x) {
        return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    };

    moneyFormatter = function(value) {
        return '£' + commify(value);
    };

    dateFormatter = function(value) {
        return moment(value).format('D MMM YYYY');
    };

    actorFormatter = function(value) {
        return '<a href="' + value.url + '">' + value.name + '</a>';
    };

    sourceFormatter = function(value) {
        return '<a href="' + value + '" target="_blank">Source</a>';
    };

    $('table').each(function(idx, tbl) {
        $(tbl).bootstrapTable({
            dataField: 'results',
            sidePagination: 'server',
            pagination: true,
            search: true,
            onLoadSuccess: function() {
                externalLinks(tbl);
            },
            responseHandler: function(res) {
                res.total = res.count;
                return res;
            }
        });
    });
});
