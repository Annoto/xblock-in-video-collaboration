/* Javascript for AnnotoXBlock. */
function AnnotoXBlock(runtime, element, options) {
    var options = options;
    var getTokenUrl = runtime.handlerUrl(element, 'get_jwt_token');

    var factory = function() {
        $(function ($) {
            var annotoAuth = function(api) {
                var api = api;
                $.ajax({
                    url: getTokenUrl,
                    method: 'GET',
                    success: function(data) {
                        if (data.status == 'ok') {
                            api.auth(data.token);
                        } else {
                            window.console && console.log('[Annoto] ERROR: ', data.msg);
                        }
                    }
                });
            }

            var setupAnnoto = function (e) {
                var el = $(e.target);
                var playerId = el.attr('id');

                var config = {
                    clientId: options.clientId,
                    position: options.horisontal,
                    features: {
                        tabs: options.tabs
                    },
                    locale: options.language,
                    rtl: options.rtl,
                    align: {
                        vertical: options.vertical,
                        horizontal: 'element_edge',
                    },
                    width: {
                        max: 400,
                    },
                    widgets: [
                        {
                            player: {
                                type: 'openedx',
                                element: playerId,
                                mediaDetails: function() {
                                    return {
                                        title: options.mediaTitle,
                                        group: {
                                            id: options.courseId,
                                            title: options.courseDisplayName,
                                            description: options.courseDescription,
                                            thumbnails: {
                                                default: window.location.origin + options.courseImage
                                            },
                                            privateThread: options.privateThread
                                        }
                                    }
                                }
                            },
                            openOnLoad: true,
                            timeline: {
                                overlayVideo: true,
                            }
                        },
                    ],
                    demoMode: options.demoMode
                };

                Annoto.on('ready', function (api) {
                    annotoAuth(api);
                });

                Annoto.boot(config);
            };

            $('.xmodule_VideoModule .video').first().on('ready', setupAnnoto);
        });
    };

    if (typeof require == 'function' && typeof Annoto != 'object') {
        require(['//app.annoto.net/annoto-bootstrap.js'], function(Annoto) {
            factory();
        });
    } else {
        factory();
    }
}
