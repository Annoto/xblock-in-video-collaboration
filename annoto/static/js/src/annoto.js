/* Javascript for AnnotoXBlock. */
function AnnotoXBlock(runtime, element, options) {
    var options = options;
    var getTokenUrl = runtime.handlerUrl(element, 'get_jwt_token');
    var element = $(element);

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
            }

            var setupAnnoto = function (e) {
                var el = $(e.target);
                var playerId = el.attr('id');
                var horizontalAlign = options.overlayVideo ? 'inner' : 'element_edge';
                var openOnLoad = true;
                var enableTabs = true;
                var videoWrapper;

                if (horizontalAlign === 'inner') {
                    videoWrapper = el.find('div.video-wrapper')[0];
                    openOnLoad = false;
                    enableTabs = false;
                }

                if (options.initialState !== 'auto') {
                    openOnLoad = !!(options.initialState === 'open');
                }

                if (options.tabs !== 'auto') {
                    enableTabs = !!(options.tabs === 'enabled');
                }

                var config = {
                    clientId: options.clientId,
                    position: options.horizontal,
                    relativePositionElement: videoWrapper,
                    features: {
                        tabs: enableTabs,
                        comments: options.comments,
                        privateNotes: options.privateNotes,
                        timeline: options.comments || options.privateNotes
                    },
                    locale: options.language,
                    rtl: options.rtl,
                    align: {
                        vertical: options.vertical,
                        horizontal: horizontalAlign,
                    },
                    width: {
                        max: 400,
                    },
                    widgets: [
                        {
                            player: {
                                type: 'openedx',
                                element: playerId,
                                params: {
                                    isLive: options.isLive
                                },
                                mediaDetails: function(details) {
                                    var extendedDetails = {
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
                                    if (details) {
                                        extendedDetails.authorName = details.authorName;
                                        extendedDetails.description = details.description;
                                    }
                                    return extendedDetails;
                                }
                            },
                            openOnLoad: openOnLoad,
                            kukuCloseOnLoad: true,
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

            if (options.videoBlockID) {
                videoElement = $('#video_' + options.videoBlockID);
                videoElement = videoElement.length && videoElement || undefined;
            }
            videoElement = videoElement || $('.xmodule_VideoBlock .video, .xmodule_VideoModule .video');
            videoElement.first().on('ready', setupAnnoto);
        });
    };

    try {
        if (typeof require == 'function' && typeof Annoto != 'object') {
            require(['//app.annoto.net/annoto-bootstrap.js'], function(Annoto) {
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
