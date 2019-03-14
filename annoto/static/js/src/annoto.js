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
                            console.log('[Annoto] ERROR: ', data.msg);
                        }
                    }
                });
            }

            var setupAnnoto = function (e) {
                var el = $(e.target);
                var playerType = 'youtube';
                var playerElem = el.find('div.video-player >:first-child');
                var playerId = playerElem.attr("id");

                if (playerElem.prop('nodeName') === 'DIV') {
                    playerType = 'html5';
                    playerId = 'html5-' + playerId;
                    playerElem.find('video').attr('id', playerId);
                }

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
                    widgets: [
                        {
                            player: {
                                type: playerType,
                                element: playerId,
                                mediaDetails: function() {
                                    return {
                                        title: options.displayName,
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
                                disableDockPadding: true,
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

            $('.video').first().on('ready', setupAnnoto);
        });
    };

    if (typeof require == "function" && typeof Annoto != "object") {
        require(['//app.annoto.net/annoto-bootstrap.js'], function(Annoto) {
            factory();
        });
    } else {
        factory();
    }
}
