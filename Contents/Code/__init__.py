import os, re, sys
import time
import datetime
import urllib, urllib2
import simplejson

SF_ROOT     = 'http://www.srf.ch'
SF_SHOWS    = SF_ROOT + '/player/tv/sendungen'
SF_CHANNELS = SF_ROOT + '/player/tv/channels'
SF_SEARCH   = SF_ROOT + '/player/tv/suche'


TITLE       = 'Schweizer Fernsehen'



REGEX_IMAGE_SUB = Regex('width=\d+')
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

####################################################################################################
def Start():
    Plugin.AddPrefixHandler('/video/schweizerfernsehen', MainMenu, TITLE)
    Plugin.AddViewGroup('InfoList', viewMode = 'InfoList', mediaType = 'items')

    ObjectContainer.title1 = TITLE
    ObjectContainer.view_group = 'InfoList'

    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
def MainMenu():
    oc = ObjectContainer()


    # GET shows from SRF
    page = HTML.ElementFromURL(SF_SHOWS)

    # LIST shows
    for show in page.xpath('//li[contains(@class, "az_item")]'):
        url = show.xpath('./a')[0].get('href')
        if url.startswith('http://') == False:
            url = SF_ROOT + url
        # Extract features title, thumbs and description
        title = show.xpath('.//a[@class="sendung_name"]/text()')[0]
        thumb = show.xpath('.//img')[0].get('src')
        thumbs = [ REGEX_IMAGE_SUB.sub(thumb, 'width=500'), thumb ]

        description = None
        try: description = show.xpath('./p[@class="az_description"]/text()')[0]
        except: pass

        oc.add(DirectoryObject(
            key = Callback(EpisodeMenu, title = title, url = url),
            title = title,
            summary = description,
            thumb = Resource.ContentsOfURLWithFallback(thumbs)))

    return oc

####################################################################################################
def EpisodeMenu(title, url):
    oc = ObjectContainer(title2 = title)

    try:
        page = HTML.ElementFromURL(url)
        show_name = page.xpath('//div[@class = "sendung_info_right"]/h1[@class = "title"]/text()')[0]

        # The most recent episode (likely to just be one)
        for episode in page.xpath('//li[@class = "sendung_item"]'):
            episode_url = episode.xpath('.//a')[1].get('href')
            Log.Debug('Episode URL: %s' %episode_url) 
            
            #Get ID for JSON   
            id = getIdFromUrl(episode_url)
            Log.Debug('ID from URL: %s' %id)
            json = getJSONForId(id)
            Log.Debug('JSON: %s' %json)   
            episode_url = getVideoFromJSON(json)
            Log.Debug('Streaming URL: %s' %episode_url)         
    
            title = ''.join(episode.xpath('.//h3[@class="title"]/text()'))

            try:
                title += ' ' + ''.join(episode.xpath('.//div[@class="title_date"]/text()'))
            except:
                pass
            
            Log.Debug('Title: %s' %title)
            thumb = episode.xpath('.//img')[0].get('data-src2x')
            Log.Debug('Thumb: %s' %thumb)
            thumbs = [ REGEX_IMAGE_SUB.sub('width=500', thumb), thumb ]
    
            description = ''.join(episode.xpath('.//div[@class="description"]/text()'))
            Log.Debug('Description: %s' %description)

            oc.add(createEpisodeObject(
                url=episode_url,
                title=title,
                summary=description,
                thumb=Resource.ContentsOfURLWithFallback(thumbs),
                show_name=show_name))
            
    except IndexError:
        pass

    if len(oc) == 0 and 'period=' not in url:
        return ObjectContainer(
            header = unicode(Locale.LocalString("No Episodes")),
            message =  unicode(Locale.LocalString("This show has no episodes available.")))

    # Add a link to the previous months content...
    try:
        if 'period=' in url:
            year_month = url.split('period=')[1]
            (year, month) = map(lambda x: int(x), year_month.split('-'))
        else:
            month_year = ''.join(page.xpath('//div[@id = "act_month_year"]/text()'))
            (month, year) = month_year.split(' ')
            now = Datetime.Now()
            year = int(year)
            month = MONTHS.index(month) + 1

        if month == 1:
            month = 12
            year = year - 1
        else:
            month = month - 1

        if 'period=' in url:
            previous_url = Regex('period=\d+-\d+').sub('period=%d-%d' % (year, month), url)
        else:
            previous_url = url + "&period=%d-%d" % (year, month)

        oc.add(DirectoryObject(
            key = Callback(EpisodeMenu, title = title, url = previous_url),
            title =  Locale.LocalString("Previous Month")))

    except: pass

    return oc


#
# parsing functions
############################################

def getIdFromUrl( url):
    return re.compile( '[\?|\&]id=([0-9a-z\-]+)').findall( url)[0]

def getUrlWithoutParams( url):
    return url.split('?')[0]

# Get JSON for the Playlist items
def fetchHttp( url, args={}, hdrs={}, post=False):
    hdrs["User-Agent"] = "Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0"
    if post:
        req = urllib2.Request( url, urllib.urlencode( args), hdrs)
    else:
        url = url + "?" + urllib.urlencode( args)
        req = urllib2.Request( url, None, hdrs)
    response = urllib2.urlopen( req)
    encoding = re.findall("charset=([a-zA-Z0-9\-]+)", response.headers['content-type'])
    text = response.read()
    if len(encoding):
        responsetext = unicode( text, encoding[0] );
    else:
        responsetext = text
    response.close()

    return responsetext


def getJSONForId(id):
    json_url = SF_ROOT + "/webservice/cvis/segment/" + id + "/.json?nohttperr=1;omit_video_segments_validity=1;omit_related_segments=1"
    url = fetchHttp(json_url).split("\n")[1]
    json = simplejson.loads(url)

    return json
    
    
# Get the high definition playlist from JSON
def getVideoFromJSON( json):
    streams = json["playlists"]["playlist"]
    sortedstreams = sorted(streams, key=lambda el: int(el["quality"]))
    Log.Debug('Number of Streams: %s' %len(sortedstreams)) 
    index = 4
    
    if (index >= len(sortedstreams)):
        index = len(sortedstreams)-2
    
    return sortedstreams[index]["url"]

def createEpisodeObject(url, title, summary, thumb, show_name=None, include_container=False):
    container = Container.MP4
    video_codec = VideoCodec.H264
    audio_codec = AudioCodec.AAC
    audio_channels = 2

    track_object = EpisodeObject(
        key = Callback(
            createEpisodeObject,
            url=url,
            title=title,
            summary=summary,
            thumb=thumb,
            show_name=show_name,
            include_container=True
        ),
        title = title,
        summary = summary,
        thumb=thumb,
        producers = [],
        show = show_name,
        items = [
            MediaObject(
                parts = [
                    PartObject(key=Callback(PlayVideo, url=url))
                ],
                container = container,
                video_codec = video_codec,
                audio_codec = audio_codec,
                audio_channels = audio_channels,
                optimized_for_streaming = True
            )
        ]
    )

    if include_container:
        return ObjectContainer(objects=[track_object])
    else:
        return track_object

@indirect
def PlayVideo(url):
    return IndirectResponse(VideoClipObject, key=url)
