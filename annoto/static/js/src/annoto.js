/* Javascript for AnnotoXBlock. */
function AnnotoXBlock(runtime, element, options) {
    var options = options;
    var getTokenUrl = runtime.handlerUrl(element, 'get_jwt_token');
    var element = $(element);
    var config;

    var factory = function() {
        $(function ($) {
            var videoElement;
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
                            element.find('.annoto-block').html('Error loading Annoto XBlock.');
                        }
                    }
                });
            };

            var setupAnnoto = function (e) {
                var el = $(e.target);
                var annotoElement = {
                    'openedx': `#${el.attr('id')}`,
                    'page': document.body
                };

                window.console && console.log("AnnotoxBlock: Object Type is: " + options.objectType);
                window.console && console.log("AnnotoxBlock: Element is: " + annotoElement[options.objectType]);
                
                config = {
                    clientId: options.clientId,
                    locale: options.language,
                    hooks: {
                        mediaDetails: function() {
                            const details = {
                                title: options.mediaTitle,
                                //description: TBD,
                            };
                            if (options.objectType == 'page') {
                                details.id = location.href;
                            }
                            return {
                                details,
                            };
                        },
                    },
                    group: {
                        id: options.courseId,
                        title: options.courseDisplayName,
                        description: options.courseDescription,
                    },
                    widgets: [
                        {
                            player: {
                                type: options.objectType,
                                element: annotoElement[options.objectType],
                                params: {
                                    isLive: options.isLive
                                },
                            },
                            timeline: {
                                overlay: (options.objectType === 'openedx'),
                            }
                        },
                    ],
                };

                Annoto.annotoApi ? loadChatPlugin(): initChatPlugin();

            };

            var initChatPlugin = function (e) {
                Annoto.on('ready', function (api) {
                    Annoto.annotoApi = api;
                    annotoAuth(api);
                });
                
                Annoto.boot(config);
            };

            var loadChatPlugin = function (e) {
                return Annoto.annotoApi.load(config);
            };


            if (options.videoBlockID) {
                window.console && console.log("AnnotoxBlock: videoBlockID is: " + options.videoBlockID);
                videoElement = $('#video_' + options.videoBlockID);
                videoElement = videoElement.length && videoElement || undefined;
                window.console && console.log("AnnotoxBlock: videoElement is: ");
                window.console && console.log(videoElement);

            }
            videoElement = videoElement || $('.xmodule_VideoBlock .video, .xmodule_VideoModule .video');

            if (options.objectType == 'openedx') {
                window.console && console.log("AnnotoxBlock: videoElement is: ");
                window.console && console.log(videoElement);

                videoElement.first().on('ready', setupAnnoto);
            } else {
                setupAnnoto($(document));
            }
        });
    };
    
    try {
        if (typeof require == 'function' && typeof Annoto != 'object') {
            require(['//cdn.annoto.net/widget/latest/bootstrap.js'], function(Annoto) {
                factory();
            });
        } else {
            factory();
        }
    } catch (err) {
        element.find('.annoto-block').html('Error loading Annoto XBlock.');
        throw err;
    }
}
